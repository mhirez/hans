"""Every tunable number in one place, so balancing never means hunting through code.

Distances are in tiles, times in seconds. Nothing in the AI packages knows about pixels;
only the ui package multiplies by TILE.
"""

TITLE = "Hans"

# --- Screen layout -------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TILE = 34
COLS, ROWS = 22, 18
HEADER_H = 54                      # strip above the arena
ARENA_X, ARENA_Y = 0, HEADER_H
ARENA_W, ARENA_H = COLS * TILE, ROWS * TILE   # 748 x 612
FOOTER_Y = ARENA_Y + ARENA_H       # 666
PANEL_X = ARENA_W                  # 748
PANEL_W = WIDTH - PANEL_X          # 532

# --- Cues ----------------------------------------------------------------------------
CUES = ("owner", "scent", "crowd")
CUE_LABELS = {"owner": "Von Osten's posture", "scent": "Scent", "crowd": "Crowd murmur"}
CUE_SHORT = {"owner": "von Osten", "scent": "scent", "crowd": "crowd"}
N_DOORS = 3
ROMAN = ("I", "II", "III")

# --- Hans's body and patience (his motivation) ---------------------------------------
HANS_SPEED = 3.5            # tiles per second
STUDY_TIME = 1.2            # seconds spent studying one cue source up close
PATIENCE = 14.0             # seconds Hans will spend gathering information
CROWD_PATIENCE_DRAIN = 1.3  # a watching crowd makes Hans restless
MIN_OBSERVE_TIME = 1.0      # Hans always takes in the scene before acting
PASSIVE_SENSE_INTERVAL = 0.4
DECIDE_TIME = 0.9           # visible "thinking" pause
TAP_INTERVAL = 0.38
REVEAL_TIME = 1.8
START_DELAY = 0.6

# --- Perception ----------------------------------------------------------------------
VISUAL_RANGE = 20.0
VISUAL_PASSIVE_MAX = 0.9
VISUAL_FOCUSED = 0.95
BLINKERS_FOCUSED = 0.45     # blinkers: Hans must walk right up and crane his neck
SCENT_RANGE = 2.5
SCENT_PASSIVE_MAX = 0.8
SCENT_FOCUSED = 0.9
SOUND_RANGE = 25.0
SOUND_PASSIVE_MAX = 0.5
SOUND_PASSIVE_FLOOR = 0.3
SOUND_FOCUSED = 0.85
MISREAD_RATE = 0.4          # chance of misreading = (1 - clarity) * MISREAD_RATE
MIN_CLARITY = 0.05
FOCUSED_CLARITY = {"owner": VISUAL_FOCUSED, "scent": SCENT_FOCUSED, "crowd": SOUND_FOCUSED}

# --- Signal strengths emitted by the world -------------------------------------------
OWNER_SURE = 0.9            # von Osten believes he knows (truly or misled)
OWNER_GUESS = 0.5           # von Osten is guessing: weaker, but Hans can't tell why
CROWD_SAW = 0.75
CROWD_GUESS = 0.6
SCENT_PRESENT = 0.85
SCENT_ABSENT = 0.6
NEGATIVE_EVIDENCE_SCALE = 0.5   # "no scent here" counts half as much as "carrot here"

# --- Learning (Beta trust per cue type) ----------------------------------------------
PRIOR = 1.0                 # alpha = beta = 1  ->  trust 0.5, maximum uncertainty
DECAY = 0.97                # per trial, evidence fades back toward the prior

# --- Attention and decision (utility) ------------------------------------------------
CURIOSITY = 0.6             # bonus for studying cue types Hans is unsure about
TRAVEL_COST = 0.04          # utility lost per second of walking
INVESTIGATE_THRESHOLD = 0.1
CONFIDENT_MARGIN = 0.45     # Hans stops looking once one door is this far ahead
MAX_INVESTIGATIONS = 5

# --- Cases ---------------------------------------------------------------------------
INVESTIGATION_TRIALS = 10
TRAINING_TRIALS = 60
TRUTH_MARGIN = 0.1          # a case's answer must lead the runner-up by this much
FAST_FORWARD = 3
