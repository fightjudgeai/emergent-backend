"""
Base weights and multipliers for Scoring Engine V2
"""

# =============================================================================
# STRIKE BASE WEIGHTS (Plan A Striking)
# =============================================================================

STRIKE_BASE_WEIGHTS = {
    "jab": 1.0,
    "cross": 2.0,
    "hook": 2.2,
    "uppercut": 2.2,
    "overhand": 2.2,
    "head_kick": 3.0,
    "body_kick": 3.0,
    "leg_kick": 1.5,
    "elbow": 2.5,
    "knee": 2.5,
    "ground_strike": 2.0,  # Default for ground strikes
    "ground_strike_bottom": 1.5,  # Strikes from bottom position
}

# =============================================================================
# QUALITY MULTIPLIERS
# =============================================================================

QUALITY_MULTIPLIERS = {
    "LIGHT": 0.50,
    "SOLID": 1.00,
}

# =============================================================================
# HEAVY STRIKES (for gate counting)
# These count toward heavy strike differential for 10-8/10-7 gates
# =============================================================================

HEAVY_STRIKE_TECHNIQUES = {
    "head_kick",
    "body_kick",
    "elbow", 
    "knee",
    "hook",
    "uppercut",
    "overhand",
    "cross",
}

# =============================================================================
# GRAPPLING WEIGHTS (Plan A Grappling)
# =============================================================================

GRAPPLING_WEIGHTS = {
    "takedown": 2.0,
    "takedown_stuffed": 0.8,  # Defensive credit
}

SUBMISSION_WEIGHTS = {
    "LIGHT": 0.5,
    "DEEP": 1.5,
    "NEAR_FINISH": 3.0,
}

# =============================================================================
# CONTROL SCORING RATES (points per second)
# =============================================================================

CONTROL_RATES = {
    "TOP": 0.05,    # Top control
    "BACK": 0.06,   # Back control (highest)
    "CAGE": 0.02,   # Cage control (lowest, Plan C only)
}

# Control-with-offense multiplier
# Applied when controlling fighter logs >= 1 SOLID strike or sub attempt
CONTROL_OFFENSE_MULTIPLIER = 1.10

# =============================================================================
# IMPACT EVENT VALUES
# =============================================================================

IMPACT_VALUES = {
    "KD_FLASH": 4.0,
    "KD_HARD": 8.0,
    "KD_NF": 10.0,
    "ROCKED": 3.0,
}

# =============================================================================
# LEG DAMAGE INDEX (LDI) ESCALATION
# =============================================================================

# Each leg kick adds 0.5 to LDI against opponent
LDI_INCREMENT = 0.5

# LDI multiplier brackets
LDI_MULTIPLIERS = {
    (0, 5): 1.00,    # LDI 0-5: no bonus
    (6, 9): 1.10,    # LDI 6-9: 10% bonus
    (10, 999): 1.25, # LDI 10+: 25% bonus
}

def get_ldi_multiplier(ldi: float) -> float:
    """Get the leg kick multiplier based on current LDI"""
    for (low, high), mult in LDI_MULTIPLIERS.items():
        if low <= ldi <= high:
            return mult
    return 1.0

# =============================================================================
# PLAN B/C THRESHOLDS
# =============================================================================

# Plan B can only be considered if |delta_plan_a| < this value
PLAN_B_THRESHOLD = 2.0

# Plan B contribution cap
PLAN_B_CAP = 1.0

# Each aggression event value (if tracked)
AGGRESSION_EVENT_VALUE = 0.2

# Plan C can only be considered if |delta_plan_a + delta_plan_b| < this value
PLAN_C_THRESHOLD = 1.0

# =============================================================================
# 10-POINT MUST MAPPING THRESHOLDS
# =============================================================================

# Draw threshold - if |delta| < this AND no impact advantage
DRAW_THRESHOLD = 0.5

# Note: 10-8 and 10-7 are determined by gates, not thresholds

# =============================================================================
# 10-8 GATE REQUIREMENTS
# =============================================================================

GATE_10_8 = {
    # Impact requirement (must meet ONE of these)
    "min_total_kd": 3,  # >=3 knockdowns (flash/hard combined)
    "alt_kd_hard_min": 3,  # OR >=3 KD_HARD
    "alt_kd_nf_min": 2,    # AND >=2 KD_NF or SUB_NF
    "alt_sub_nf_min": 3,   # OR >=3 SUB_NF with heavy strike dominance
    
    # Differential requirement (must meet ONE of these)
    "min_plan_a_lead": 4.0,
    "min_solid_heavy_differential": 12,  # (winner - loser) SOLID+HEAVY strikes
    "min_heavy_strike_advantage": 5,
}

# =============================================================================
# 10-7 GATE REQUIREMENTS
# =============================================================================

GATE_10_7 = {
    # Severe impact requirement (must meet ONE of these)
    "min_total_kd": 4,  # >=4 knockdowns
    "alt_kd_hard_min": 3,
    "alt_nf_sequence_min": 4,  # >=4 near-finish sequences
    "alt_nf_kd_sequence_min": 3,  # >=3 "NF + KD in same sequence"
    
    # Massive differential requirement (must meet ONE of these)
    "min_plan_a_lead": 8.0,
    "min_solid_heavy_differential": 25,
    "min_heavy_strike_advantage": 10,
}

# Near-finish sequence window (seconds) - KD events within this window count as sequence
NF_SEQUENCE_WINDOW_SECONDS = 15.0
