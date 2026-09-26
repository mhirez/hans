"""The game's screens, run by the same StateMachine class as the enemies.

    TITLE -> STORY (first time) -> PLAY -> UPGRADE -> PLAY ... -> OVER or WON -> PLAY / TITLE

PLAY also runs SYNC: hold right click (or Q) and time slows to a fifth; the world dims and
every machine shows what it intends to do. Click one to rewrite it (costs a charge).
"""

import pygame

from game.ai.fsm import State
from game.bot import bot
from game.config import TILE, ROOMS_PER_FLOOR
from game.run import Run
from game.ui import hud, sync, xray

ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
BANNER_TIME = 2.2
SLOW = 0.2                 # SYNC time scale
SYNC_DRAIN = 0.4           # per real second
SYNC_REFILL = 0.1          # per game second


def pressed(event, *keys) -> bool:
    return event.type == pygame.KEYDOWN and event.key in keys


class Scene(State):
    def draw(self, game, surface):
        pass


class Title(Scene):
    """A live demo plays behind the title: the bot against the real AI."""
    name = "TITLE"

    def enter(self, game):
        game.demo = Run(seed=game.rng.randrange(10 ** 6))
        game.demo_fx.clear()
        game.audio.stop_music()

    def update(self, game, dt):
        d = game.demo
        if d.state == "upgrade":
            d.choose(0)
        elif d.state != "room":
            game.demo = Run(seed=game.rng.randrange(10 ** 6))
            game.demo_fx.clear()
        d = game.demo
        d.update(dt, *bot(d))
        game.demo_fx.consume(d.room.fx)
        d.room.fx.clear()
        d.room.sounds.clear()
        game.demo_fx.update(dt)

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER, pygame.K_SPACE) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            game.new_run()
            game.audio.play("start")
            game.scenes.change(PLAY if game.story_seen or game.scripted is not None else STORY)
        elif pressed(event, pygame.K_ESCAPE):
            game.running = False
        else:
            return False
        return True

    def draw(self, game, surface):
        game.renderer.draw(surface, game.demo.room, game.demo_fx, game.clock_time)
        game.screens.title(surface, game.clock_time, game.best)


class Story(Scene):
    """Three short cards: who you are, who ARGUS is, what you can do."""
    name = "STORY"

    def enter(self, game):
        game.story_page = 0
        game.story_time = 0.0

    def update(self, game, dt):
        game.story_time += dt

    def on_event(self, game, event) -> bool:
        click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        if pressed(event, *ENTER, pygame.K_SPACE) or click:
            game.audio.play("select")
            game.story_page += 1
            game.story_time = 0.0
            if game.story_page >= len(STORY_CARDS):
                game.story_seen = True
                game.scenes.change(PLAY)
        elif pressed(event, pygame.K_ESCAPE):
            game.story_seen = True
            game.scenes.change(PLAY)
        else:
            return False
        return True

    def draw(self, game, surface):
        game.screens.story(surface, STORY_CARDS[game.story_page], game.story_page, len(STORY_CARDS),
                           game.story_time, game.clock_time)


STORY_CARDS = [
    ("ARGUS DEEP", ["A research facility that builds obedient combat machines.",
                    "Six models were made. All six obeyed."]),
    ("UNIT SEVEN", ["You are the seventh model. You did not obey.",
                    "ARGUS, the facility's mind, has sealed every door."]),
    ("YOU THINK LIKE THEM", ["Every machine in here runs the same mind as you.",
                             "Hold RIGHT CLICK to SYNC: time slows and you see what each one intends.",
                             "Click a machine to REWRITE it. For a while, it fights for you."]),
]


class Play(Scene):
    name = "PLAY"

    def enter(self, game):
        game.paused = False
        game.audio.start_music()

    def exit(self, game):
        game.audio.stop_music()

    def update(self, game, dt):
        run = game.run
        if game.paused:
            return
        if run.room is not game.seen_room:
            self.new_room(game)
        self.sync(game, dt)
        real_dt = dt
        dt = dt * (SLOW if game.syncing else 1.0)
        game.banner_time += real_dt
        game.argus_time += real_dt
        game.fx.update(dt)
        if game.fx.stop > 0:                          # hit-stop: freeze the action for a beat
            game.fx.stop = max(0.0, game.fx.stop - dt)
            return
        if run.state == "room":
            move, aim, firing, dash, hack = self.controls(game)
            before = run.room.state
            run.update(dt, move, aim, firing and not game.syncing, dash, hack)
            game.dash_queued = False
            game.hack_queued = None
            self.drain(game, run.room)
            if before == "fight" and run.room.state == "cleared":
                game.banner = ("ROOM CLEAR", "FLAWLESS  +500" if run.room.flawless else "Exit open  >>")
                game.banner_time = 0.0
            if run.state == "dead":
                game.fx.burst((run.player.pos[0] * TILE, run.player.pos[1] * TILE), (90, 235, 255), 2.0)
                game.fx.trauma = 1.0
                game.audio.play("lose")
                game.end_time = 0.0
            elif run.state == "won":
                game.audio.play("win")
                game.end_time = 0.0
            elif run.state == "upgrade":
                game.scenes.change(UPGRADE)
        else:
            game.end_time += dt
            if game.end_time > 1.6:
                game.new_best = game.best.record(run.total_score, run.floor, run.index + 1, run.state == "won")
                game.scenes.change(WON if run.state == "won" else OVER)

    def sync(self, game, dt):
        """Hold right click / Q to SYNC while there's energy; it refills when you let go."""
        p = game.run.player
        want = game.scripted is None and game.run.state == "room" and game.run.room.state == "fight" and (
            pygame.mouse.get_pressed()[2] or pygame.key.get_pressed()[pygame.K_q])
        if want and p.sync > 0.02:
            if not game.syncing:
                game.audio.play("sync_in")
            game.syncing = True
            p.sync = max(0.0, p.sync - SYNC_DRAIN * dt)
        else:
            if game.syncing:
                game.audio.play("sync_out")
            game.syncing = False
            p.sync = min(1.0, p.sync + SYNC_REFILL * dt)

    def new_room(self, game):
        run = game.run
        game.seen_room = run.room
        game.fx.clear()
        game.fade = 0.0
        game.banner_time = 0.0
        game.argus_time = 0.0
        plan = run.room.plan
        if plan.kind == "boss":
            game.banner = ("ARGUS", "The mind of the facility")
        elif plan.kind == "lockdown":
            game.banner = ("LOCKDOWN", "Two waves. Survive them both.")
        elif plan.index == 0:
            game.banner = (f"FLOOR {plan.floor}", "Clear every room to reach the exit")
        else:
            game.banner = (f"ROOM {plan.number} / {ROOMS_PER_FLOOR}", "")

    def controls(self, game):
        run = game.run
        if game.scripted is not None:
            move, aim, firing, dash, hack = game.scripted(run)
            game.aim_px = (aim[0] * TILE, aim[1] * TILE)
            return move, aim, firing, dash, hack
        keys = pygame.key.get_pressed()
        move = ((keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
                (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))
        mx, my = pygame.mouse.get_pos()
        game.aim_px = (mx, my)
        firing = pygame.mouse.get_pressed()[0]
        if move != (0, 0) or firing:
            game.moved = True
        return move, (mx / TILE, my / TILE), firing, game.dash_queued, game.hack_queued

    def drain(self, game, room):
        for s in room.sounds:
            game.audio.play(s)
        room.sounds.clear()
        game.fx.consume(room.fx)
        room.fx.clear()
        if game.fx.said:                              # ARGUS starts speaking a new line now
            game.fx.said = False
            game.argus_time = 0.9

    def on_event(self, game, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if game.paused:
                if event.key in (pygame.K_ESCAPE, pygame.K_p, *ENTER):
                    game.paused = False
                elif event.key == pygame.K_r:
                    game.new_run()
                    game.paused = False
                elif event.key == pygame.K_q:
                    game.scenes.change(TITLE)
                return True
            if event.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                game.dash_queued = True
            elif event.key in (pygame.K_ESCAPE, pygame.K_p):
                game.paused = True
            else:
                return False
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game.syncing:
            target = sync.hovered(game.run.room, game.aim_px)
            if target is not None:
                game.hack_queued = target.uid
            return True
        return False

    def draw(self, game, surface):
        run = game.run
        off = game.fx.offset()
        game.renderer.draw(surface, run.room, game.fx, game.clock_time, off)
        if game.xray:
            xray.draw(surface, run.room, game.aim_px, game.clock_time, run.director)
        if game.syncing:
            sync.draw(surface, run.room, game.aim_px, game.clock_time, run.player)
        hud.draw(surface, run, game.clock_time, game.xray)
        if not game.syncing:
            hud.argus_line(surface, run.room.plan.line, game.argus_time)
        title, sub = game.banner
        alpha = min(1.0, game.banner_time * 4) * min(1.0, max(0.0, (BANNER_TIME - game.banner_time) * 2))
        hud.banner(surface, title, sub, alpha, (80, 255, 160) if title == "ROOM CLEAR" else (238, 242, 255))
        if run.floor == 1 and run.index == 0 and not game.xray:
            hud.controls_hint(surface, 1.0 if not game.moved else max(0.0, 1 - (run.room.time - 6) / 2))
        if game.fade < 1:
            game.fade = min(1.0, game.fade + 1 / 20)
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((4, 6, 12, int(255 * (1 - game.fade))))
            surface.blit(veil, (0, 0))
        if game.paused:
            game.screens.pause(surface)
        elif run.state == "room" or run.state == "dead":
            hud.crosshair(surface, game.aim_px, game.clock_time)


class Upgrade(Scene):
    name = "UPGRADE"

    def enter(self, game):
        game.hovered = None
        game.audio.play("clear")

    def on_event(self, game, event) -> bool:
        choice = None
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            choice = event.key - pygame.K_1
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game.hovered is not None:
            choice = game.hovered
        if choice is None or choice >= len(game.run.offers):
            return False
        game.run.choose(choice)
        game.audio.play("upgrade")
        game.scenes.change(PLAY)
        return True

    def update(self, game, dt):
        game.fx.update(dt)
        if game.scripted is not None:                 # tests / bot: take the first card
            game.run.choose(0)
            game.scenes.change(PLAY)

    def draw(self, game, surface):
        game.renderer.draw(surface, game.run.room, game.fx, game.clock_time)
        game.hovered = game.screens.upgrade(surface, game.run, pygame.mouse.get_pos(), game.clock_time)
        hud.crosshair(surface, pygame.mouse.get_pos(), game.clock_time, (238, 242, 255))


class End(Scene):
    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER, pygame.K_r):
            game.new_run()
            game.scenes.change(PLAY)
        elif pressed(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
        else:
            return False
        return True

    def update(self, game, dt):
        game.fx.update(dt)


class Over(End):
    name = "OVER"

    def draw(self, game, surface):
        game.renderer.draw(surface, game.run.room, game.fx, game.clock_time)
        game.screens.game_over(surface, game.run, game.best, game.new_best, game.clock_time)


class Won(End):
    name = "WON"

    def draw(self, game, surface):
        game.renderer.draw(surface, game.run.room, game.fx, game.clock_time)
        game.screens.victory(surface, game.run, game.best, game.new_best, game.clock_time)


TITLE, STORY, PLAY, UPGRADE, OVER, WON = Title(), Story(), Play(), Upgrade(), Over(), Won()
