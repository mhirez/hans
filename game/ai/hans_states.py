"""Hans's behaviour as a finite state machine (6 states).

    state          leaves when                                        goes to
    WAITING        the scientist runs a trial ("start")               OBSERVING
                   (between trials he trots back to his spot)
    OBSERVING      he is sure enough of one door / patience gone      DECIDING
                   a source is worth a closer look (VOI > cost)       INVESTIGATING
                   nothing is worth the walk                          DECIDING
    INVESTIGATING  studied the source (walk with A*, then study)      OBSERVING
                   patience gone                                      DECIDING
    DECIDING       thinking pause over                                ANSWERING
    ANSWERING      walked to the door and tapped its number           LEARNING
    LEARNING       carrot revealed, trust updated                     WAITING

States append simple event names to `hans.events` ("tap", "sniff", "correct", ...);
the game turns them into sounds. The AI itself never touches pygame.
"""

from game.config import (START_DELAY, MIN_OBSERVE_TIME, DECIDE_TIME, TAP_INTERVAL, REVEAL_TIME,
                         STUDY_TIME, ROMAN)
from game.ai.state_machine import State
from game.world import START, tile_of, distance

STUDY_VERBS = {"owner": "studies", "scent": "sniffs at", "crowd": "listens to"}
COUNT_WORDS = ("one", "two", "three")


class Waiting(State):
    name = "WAITING"

    def enter(self, hans):
        hans.returning = distance(hans.pos, START) > 0.1 and hans.walk_to(tile_of(START), final=START)

    def update(self, hans, dt):
        if hans.returning and hans.step(dt):
            hans.returning = False
            hans.facing = -1

    def on_event(self, hans, event) -> bool:
        if event == "start":
            hans.fsm.change(OBSERVING)
            return True
        return False


class Observing(State):
    name = "OBSERVING"

    def enter(self, hans):
        hans.caption = "Hans takes in the courtyard..." if hans.first_look else "Hans considers..."

    def update(self, hans, dt):
        hans.drain_patience(dt)
        hans.sense(dt)
        settle = START_DELAY + MIN_OBSERVE_TIME if hans.first_look else 0.35
        if hans.fsm.time_in_state < settle:
            return
        hans.first_look = False
        if hans.patience <= 0:
            hans.caption = "Hans runs out of patience."
            hans.fsm.change(DECIDING)
        elif hans.mind.confident():
            hans.fsm.change(DECIDING)
        else:
            option = hans.mind.plan_attention(hans.senses, hans.travel_times(), hans.patience)
            if option is None:
                hans.fsm.change(DECIDING)
            else:
                hans.target = hans.world.source(option.source_id)
                hans.fsm.change(INVESTIGATING)


class Investigating(State):
    name = "INVESTIGATING"

    def enter(self, hans):
        hans.study_left = STUDY_TIME
        hans.studying = False
        hans.route_failed = not hans.walk_to(hans.target.observe_tile)
        hans.caption = f"Hans walks over to {hans.target.label}."

    def update(self, hans, dt):
        hans.drain_patience(dt)
        hans.sense(dt)
        if hans.route_failed:
            hans.mind.studied.append(hans.target.id)
            hans.fsm.change(OBSERVING)
            return
        if hans.patience <= 0:
            hans.caption = "Hans runs out of patience."
            hans.fsm.change(DECIDING)
            return
        if not hans.step(dt):
            return
        if not hans.studying:
            hans.studying = True
            hans.events.append("sniff" if hans.target.cue == "scent" else "study")
        hans.face(hans.target.pos)
        hans.caption = f"Hans {STUDY_VERBS[hans.target.cue]} {hans.target.label}."
        hans.study_left -= dt
        if hans.study_left <= 0:
            hans.mind.study(hans.senses, hans.target, hans.pos)
            hans.fsm.change(OBSERVING)

    def exit(self, hans):
        hans.target = None
        hans.studying = False


class Deciding(State):
    name = "DECIDING"

    def enter(self, hans):
        d = hans.mind.decide()
        hans.caption = {"CONFIDENT": "Hans makes up his mind.",
                        "UNSURE": "Hans hesitates...",
                        "GUESS": "Hans has nothing to go on. He guesses."}[d.mode]

    def update(self, hans, dt):
        if hans.fsm.time_in_state >= DECIDE_TIME:
            hans.fsm.change(ANSWERING)


class Answering(State):
    name = "ANSWERING"

    def enter(self, hans):
        door = hans.world.doors[hans.mind.decision.choice]
        hans.walk_to(door.front_tile, final=door.front)
        hans.taps_done = 0
        hans.tap_timer = 0.0
        hans.caption = f"Hans trots to door {door.name}."

    def update(self, hans, dt):
        if not hans.step(dt):
            return
        choice = hans.mind.decision.choice
        hans.tapping = True
        hans.tap_timer += dt
        if hans.tap_timer >= TAP_INTERVAL:
            hans.tap_timer = 0.0
            if hans.taps_done < choice + 1:
                hans.taps_done += 1
                hans.events.append("tap")
                hans.caption = "Hans taps: " + ", ".join(COUNT_WORDS[:hans.taps_done]) + "..."
            else:
                hans.fsm.change(LEARNING)

    def exit(self, hans):
        hans.tapping = False


class Learning(State):
    name = "LEARNING"

    def enter(self, hans):
        hans.finish_trial(hans.senses.reveal())
        o = hans.outcome
        hans.events.extend(["open", "correct" if o.success else "wrong"])
        hans.caption = (f"Correct! The carrot was behind door {ROMAN[o.carrot]}." if o.success else
                        f"Wrong. The carrot was behind door {ROMAN[o.carrot]}.")

    def update(self, hans, dt):
        if hans.fsm.time_in_state >= REVEAL_TIME:
            hans.done = True
            hans.fsm.change(WAITING)


WAITING = Waiting()
OBSERVING = Observing()
INVESTIGATING = Investigating()
DECIDING = Deciding()
ANSWERING = Answering()
LEARNING = Learning()
