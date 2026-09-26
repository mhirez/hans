"""Every tunable number in one place. Distances are in tiles, times in seconds, angles in radians."""

import math

TITLE = "Hans"

# --- Screen --------------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TILE = 40
HUD_H = 60
ARENA_COLS, ARENA_ROWS = 32, 16          # 1280 x 640 under the HUD

# --- Hans ----------------------------------------------------------------------------
RUN_SPEED = 4.2
GALLOP_SPEED = 6.8
TANGLED_SPEED = 1.8                      # caught in a lasso
TANGLE_TIME = 1.8
HANS_RADIUS = 0.32
STAMINA = 2.5                            # seconds of gallop when full
STAMINA_REGEN = 0.6                      # per second while not galloping
HEARTS = 3
HURT_INVULNERABLE = 1.6
KICK_RADIUS = 1.3                        # shorter than a net: step in during the wind-up
KICK_COOLDOWN = 0.6
KICK_KNOCKBACK = 2.4
GALLOP_NOISE = 6.0                       # enemies within this many tiles hear a galloping hoof-fall
KICK_NOISE = 5.0
CRUNCH_NOISE = 4.5                       # eating a carrot isn't quiet either
MORALE_PER_KO = 0.18                     # each knockout in a wave shakes the others' nerve
WARY_HOP = 1.3                           # WARY tactic: how far they hop back from a kick
POWER_TIME = 6.0                         # golden horseshoe

# --- Enemies (shared) ----------------------------------------------------------------
VIEW_RANGE = 7.5
VIEW_HALF_ANGLE = math.radians(60)
NOTICE_TIME = 0.35                       # seconds of seeing Hans before "!" (at point blank less)
MEMORY_TIME = 3.0                        # after losing sight, how long they keep going to where he was
STUN_TIME = 1.6
REPLAN_TIME = 0.25
SEARCH_TIME = 2.5
TURN_SPEED = 7.0                         # radians per second
CONE_RAYS = 24                           # rays per vision cone drawn in the X-Ray
ENEMY_RADIUS = 0.3

# Scientist: butterfly net, chases and swings
SCIENTIST_HP = 2
SCIENTIST_WANDER = 1.6
SCIENTIST_CHASE = 3.7
NET_REACH = 1.6
NET_WINDUP = 0.55
NET_RECOVER = 0.7

# Stable boy: lasso, keeps distance, hides
LASSO_HP = 2
LASSO_WANDER = 1.7
LASSO_MOVE = 3.0
LASSO_BEST_RANGE = (3.5, 6.5)
LASSO_WINDUP = 0.75
LASSO_RELOAD = 1.8
LASSO_SPEED = 7.5
LASSO_SPREAD = 0.14                      # radians of human error in a throw
LASSO_RANGE = 8.0

# Guard dog: pack hunter, surrounds and pounces
DOG_HP = 1
DOG_WANDER = 2.2
DOG_RUN = 4.8
DOG_RING = 2.4                           # radius of the circle the pack forms around Hans
DOG_POUNCE_WINDUP = 0.35
DOG_POUNCE_SPEED = 10.0
DOG_POUNCE_DISTANCE = 3.0
DOG_RETREAT_TIME = 1.2
DOG_SMELL = 5.5                          # dogs find Hans by smell: no line of sight needed
PRINT_EVERY = 0.45                       # Hans leaves a hoofprint every this many tiles
PRINT_LIFE = 14.0                        # prints fade away after this long
PRINT_FRESH = 11.0                       # a dog will pick up prints younger than this
PRINT_SNIFF = 3.0                        # ...within this many tiles

# --- Items ---------------------------------------------------------------------------
CARROTS_ON_FIELD = 3
ITEM_RADIUS = 0.6
SUGAR_EVERY = 25.0                       # heals a heart
HORSESHOE_EVERY = 38.0                   # golden horseshoe: power
COFFEE_EVERY = 20.0                      # enemies drink it to recover
COFFEE_HEAL = 1

# --- Scoring -------------------------------------------------------------------------
CARROT_POINTS = 10
KO_POINTS = 25
WAVE_BONUS = 100
