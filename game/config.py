"""Every tunable number in one place. Distances are in tiles, times in seconds, angles in radians."""

import math

TITLE = "Hans"

# --- Screen --------------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TILE = 40
HUD_H = 56                          # objective bar across the top
PLAY_Y = HUD_H
PLAY_H = HEIGHT - HUD_H             # 664: room for 16 rows

# --- Hans (the player) ---------------------------------------------------------------
WALK_SPEED = 3.0
TROT_SPEED = 5.2                    # faster than a chasing scientist, but loud
HANS_RADIUS = 0.3
STEP_WALK = 0.42                    # seconds between hoof-falls
STEP_TROT = 0.26
TROT_NOISE = 5.0                    # how far a trotting hoof-fall carries
GRAVEL_WALK_NOISE = 3.0             # gravel is noisy even at a walk
GRAVEL_TROT_NOISE = 7.5
WRONG_DOOR_NOISE = 40.0             # everyone hears an empty door bang
TAP_REACH = 1.0                     # how close to a door's front Hans must be to tap it

# --- Von Osten ------------------------------------------------------------------------
HINT_RADIUS = 2.2
HINT_TIME = 1.4                     # seconds in his circle before he nods
HINT_DECAY = 0.25                   # progress lost per second outside the circle
OWNER_SPEED = 1.3
OWNER_STAND_TIME = 5.0              # how long he stands at each stop (wandering levels)

# --- Scientists -----------------------------------------------------------------------
PATROL_SPEED = 1.7
INVESTIGATE_SPEED = 2.3
CHASE_SPEED = 3.9                   # faster than a walk, slower than a trot
VIEW_RANGE = 6.0
VIEW_HALF_ANGLE = math.radians(34)
CLOSE_RANGE = 1.5                   # this close and in view: no doubt at all
SUSPICION_RATE = 1.8                # per second at point-blank; less when far away
SUSPICION_DECAY = 0.25
TROT_VISIBILITY = 1.6               # a trotting horse is easier to notice
WAYPOINT_PAUSE = 1.2
LOOK_AROUND_TIME = 2.6
SUSPICIOUS_GIVE_UP = 1.3            # out of sight this long while suspicious -> go and look
LOSE_SIGHT_TIME = 2.5               # out of sight this long while chasing -> search
ALERT_RADIUS = 9.0                  # a whistle brings colleagues this close
CATCH_DISTANCE = 0.6
REPLAN_TIME = 0.3
TURN_SPEED = 5.0                    # radians per second
SENTRY_SWEEP = 0.9                  # a stationary scientist sweeps +- this far
CONE_RAYS = 30

# --- Difficulty assist ----------------------------------------------------------------
ASSIST_AFTER = 2                    # failed attempts per assist step
ASSIST_MAX = 2
ASSIST_SLOWDOWN = 0.12              # scientists lose this much speed per step
ASSIST_CALM = 0.2                   # ...and get suspicious this much more slowly
