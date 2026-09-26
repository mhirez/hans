"""Every tunable number in one place. Distances are in tiles, times in seconds."""

import math

TITLE = "MISALIGNED"
WIDTH, HEIGHT = 1280, 720
FPS = 60
TILE = 40
COLS, ROWS = 32, 18                    # one room fills the screen exactly

# --- the player ---------------------------------------------------------------------------
PLAYER_RADIUS = 0.3
PLAYER_SPEED = 6.0
PLAYER_ACCEL = 70.0
PLAYER_FRICTION = 55.0
PLAYER_HP = 6
FIRE_RATE = 6.0                        # shots per second
BULLET_SPEED = 20.0
BULLET_DAMAGE = 1.0
BULLET_SPREAD = math.radians(2.5)
DASH_SPEED = 19.0
DASH_TIME = 0.13
DASH_COOLDOWN = 0.7
HURT_INVULNERABLE = 0.9
AMBUSH_MULTIPLIER = 2.0                # damage against an enemy that hasn't noticed you
SHOT_NOISE = 11.0                      # how far a gunshot is heard

# --- enemy senses -------------------------------------------------------------------------
VIEW_RANGE = 10.0
VIEW_HALF_ANGLE = math.radians(50)     # 100 degree cone while unaware
ALERT_HALF_ANGLE = math.radians(110)   # scanning around once alert
NOTICE_TIME = 0.5                      # seconds in view before "!" (faster up close)
PROXIMITY = 1.6                        # felt, not seen
MEMORY_TIME = 5.0                      # out of sight this long -> search
ALERT_RADIUS = 9.0                     # a spotter's shout reaches this far
TURN_RATE = 8.0                        # radians per second

# --- combat pacing ------------------------------------------------------------------------
ATTACK_SLOTS = 2                       # at most this many enemies attacking at once (floor 1)
ATTACK_GAP = 0.35                      # and never two attacks starting closer than this
LOCK_TIME = 0.25                       # every telegraph flashes white and locks for its last 0.25 s
ENEMY_BULLET_RADIUS = 0.16
ENEMY_BULLET_SPEED = 10.0

# --- rooms --------------------------------------------------------------------------------
ROOMS_PER_FLOOR = 4
FLOORS = 3                             # the Warden waits at the end of floor 3
