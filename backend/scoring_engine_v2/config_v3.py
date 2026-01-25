"""
FightJudge.AI Scoring Model v3.0 - Impact-First Configuration
All weights and rules are config-driven for easy tuning.
"""

# =============================================================================
# EVENT CATALOG + POINT VALUES
# =============================================================================

SCORING_CONFIG = {
    "version": "3.0",
    "name": "Impact-First v1.0",
    
    # -------------------------------------------------------------------------
    # STRIKING (STAND-UP)
    # -------------------------------------------------------------------------
    "striking": {
        "jab": {"points": 1.5, "category": "striking", "label": "Jab", "is_ss": False},
        "ss_jab": {"points": 2, "category": "striking", "label": "SS Jab", "is_ss": True},
        "cross": {"points": 3, "category": "striking", "label": "Cross", "is_ss": False},
        "ss_cross": {"points": 4.5, "category": "striking", "label": "SS Cross", "is_ss": True},
        "hook": {"points": 3, "category": "striking", "label": "Hook", "is_ss": False},
        "ss_hook": {"points": 4.5, "category": "striking", "label": "SS Hook", "is_ss": True},
        "uppercut": {"points": 3, "category": "striking", "label": "Uppercut", "is_ss": False},
        "ss_uppercut": {"points": 4.5, "category": "striking", "label": "SS Uppercut", "is_ss": True},
        "kick": {"points": 4, "category": "striking", "label": "Kick", "is_ss": False},
        "ss_kick": {"points": 6, "category": "striking", "label": "SS Kick", "is_ss": True},
        "elbow": {"points": 4, "category": "striking", "label": "Elbow", "is_ss": False},
        "ss_elbow": {"points": 6, "category": "striking", "label": "SS Elbow", "is_ss": True},
        "knee": {"points": 4, "category": "striking", "label": "Knee", "is_ss": False},
        "ss_knee": {"points": 6, "category": "striking", "label": "SS Knee", "is_ss": True},
    },
    
    # -------------------------------------------------------------------------
    # DAMAGE / ROUND-CHANGERS (PROTECTED - High value, creates Impact Locks)
    # -------------------------------------------------------------------------
    "damage": {
        "rocked": {"points": 60, "category": "damage", "label": "Rocked", "is_protected": True},
        "kd_flash": {"points": 100, "category": "damage", "label": "KD Flash", "is_protected": True, "impact_lock": "soft"},
        "kd_hard": {"points": 150, "category": "damage", "label": "KD Hard", "is_protected": True, "impact_lock": "hard"},
        "kd_nf": {"points": 210, "category": "damage", "label": "KD Near-Finish", "is_protected": True, "impact_lock": "nf"},
    },
    
    # -------------------------------------------------------------------------
    # GRAPPLING
    # -------------------------------------------------------------------------
    "grappling": {
        "takedown": {"points": 10, "category": "grappling", "label": "Takedown", "is_ss": False},
        "takedown_stuffed": {"points": 5, "category": "grappling", "label": "TD Stuffed", "is_ss": False, "max_full_value": 3},
    },
    
    # -------------------------------------------------------------------------
    # GROUND STRIKES
    # -------------------------------------------------------------------------
    "ground_strikes": {
        "gnp_light": {"points": 1, "category": "ground_strikes", "label": "GnP Light", "is_ss": False},
        "gnp_hard": {"points": 3, "category": "ground_strikes", "label": "GnP Hard", "is_ss": False},
    },
    
    # -------------------------------------------------------------------------
    # CONTROL (Time-bucketed, points per 10 seconds)
    # -------------------------------------------------------------------------
    "control": {
        "cage_control": {"points_per_bucket": 1, "bucket_seconds": 10, "category": "control", "label": "Cage Control"},
        "top_control": {"points_per_bucket": 3, "bucket_seconds": 10, "category": "control", "label": "Top Control"},
        "back_control": {"points_per_bucket": 5, "bucket_seconds": 10, "category": "control", "label": "Back Control"},
    },
    
    # -------------------------------------------------------------------------
    # SUBMISSIONS (PROTECTED)
    # -------------------------------------------------------------------------
    "submissions": {
        "sub_light": {"points": 12, "category": "submissions", "label": "Sub Light", "is_protected": False},
        "sub_deep": {"points": 28, "category": "submissions", "label": "Sub Deep", "is_protected": False},
        "sub_nf": {"points": 60, "category": "submissions", "label": "Sub Near-Finish", "is_protected": True, "impact_lock": "sub_nf"},
    },
}

# =============================================================================
# REGULARIZATION RULES
# =============================================================================

REGULARIZATION_RULES = {
    # -------------------------------------------------------------------------
    # RULE 1: Technique Diminishing Returns (per technique, per fighter, per round)
    # -------------------------------------------------------------------------
    "technique_diminishing_returns": {
        "enabled": True,
        "thresholds": [
            {"min": 1, "max": 10, "multiplier": 1.00},
            {"min": 11, "max": 20, "multiplier": 0.75},
            {"min": 21, "max": 999, "multiplier": 0.50},
        ],
        # Techniques this applies to
        "applies_to": [
            "jab", "cross", "hook", "uppercut", "kick", "elbow", "knee",
            "ss_jab", "ss_cross", "ss_hook", "ss_uppercut", "ss_kick", "ss_elbow", "ss_knee",
            "gnp_light", "gnp_hard"
        ]
    },
    
    # -------------------------------------------------------------------------
    # RULE 2: SS Abuse Guardrail (all SS combined, per fighter, per round)
    # -------------------------------------------------------------------------
    "ss_abuse_guardrail": {
        "enabled": True,
        "thresholds": [
            {"min": 1, "max": 8, "multiplier": 1.00},
            {"min": 9, "max": 14, "multiplier": 0.75},
            {"min": 15, "max": 999, "multiplier": 0.50},
        ],
        # SS event keys
        "ss_events": ["ss_jab", "ss_cross", "ss_hook", "ss_uppercut", "ss_kick", "ss_elbow", "ss_knee"]
    },
    
    # -------------------------------------------------------------------------
    # RULE 3: Control Time Diminishing Returns (after 60s continuous)
    # -------------------------------------------------------------------------
    "control_diminishing_returns": {
        "enabled": True,
        "continuous_threshold_seconds": 60,  # After 60s continuous, apply multiplier
        "multiplier_after_threshold": 0.50,
        "bucket_gap_reset_seconds": 15,  # Gap of 15s+ resets continuous streak
    },
    
    # -------------------------------------------------------------------------
    # RULE 4: Control Without Work Discount
    # -------------------------------------------------------------------------
    "control_without_work": {
        "enabled": True,
        "control_points_threshold": 20,  # If control >= 20 points
        "required_work": {
            "min_strike_points": 10,  # OR >= 10 strike points
            "any_submission": True,    # OR any submission event
            "min_gnp_hard_points": 10, # OR >= 10 gnp_hard points
        },
        "discount_multiplier": 0.75,  # Apply 0.75 if work requirement not met
    },
    
    # -------------------------------------------------------------------------
    # RULE 5: Defensive Spam Cap (Takedown Stuffed)
    # -------------------------------------------------------------------------
    "takedown_stuffed_cap": {
        "enabled": True,
        "full_value_count": 3,  # First 3 at full value
        "multiplier_after_cap": 0.50,
    },
}

# =============================================================================
# IMPACT LOCK RULES
# =============================================================================

IMPACT_LOCK_RULES = {
    # Priority order (highest first) - strongest lock wins
    "priority_order": ["kd_nf", "kd_hard", "kd_flash", "sub_nf"],
    
    "locks": {
        "kd_flash": {
            "name": "Soft Lock",
            "delta_threshold": 50,  # Cannot lose unless opponent leads by >= 50
            "reason_code": "impact_lock_kd_flash",
        },
        "kd_hard": {
            "name": "Hard Lock",
            "delta_threshold": 110,  # Cannot lose unless opponent leads by >= 110
            "reason_code": "impact_lock_kd_hard",
        },
        "kd_nf": {
            "name": "Near-Finish Lock",
            "delta_threshold": 150,  # Cannot lose unless opponent leads by >= 150
            "reason_code": "impact_lock_kd_nf",
        },
        "sub_nf": {
            "name": "Sub Near-Finish Lock",
            "delta_threshold": 90,  # Cannot lose unless opponent leads by >= 90
            "reason_code": "impact_lock_sub_nf",
        },
    }
}

# =============================================================================
# UI TOOLTIPS / HELP TEXT
# =============================================================================

UI_TOOLTIPS = {
    "ss_definition": "Only score SS when it's clean + visible effect (snap, stumble, posture break, clear reaction). Not arm taps. Not blocked.",
    "kd_nf_definition": "Only when KD leads to clear near-finish sequence: sustained follow-up, forced defense, ref/finish threat.",
    "gnp_hard_definition": "Visible impact (head snap, posture break, meaningful damage). Not pitter-patter.",
    "sub_nf_definition": "Forced panic defense, prolonged lock, ref attention, or clear 'one more second and it's over' threat.",
}

# =============================================================================
# ROUND SCORING THRESHOLDS (10-Point Must)
# =============================================================================

ROUND_SCORING = {
    "draw_threshold": 5,  # |delta| < 5 = 10-10 draw (only if no impact)
    
    # 10-8 and 10-7 are determined by impact locks + delta thresholds
    "score_10_8": {
        "requires_impact": True,  # Must have impact event
        "min_impact_events": 2,   # At least 2 protected events OR
        "min_delta": 100,         # OR delta >= 100
    },
    "score_10_7": {
        "requires_impact": True,
        "min_impact_events": 3,   # At least 3 protected events OR
        "min_delta": 200,         # OR delta >= 200
    },
}

# =============================================================================
# EVENT KEY MAPPING (Legacy -> New)
# =============================================================================

LEGACY_EVENT_MAP = {
    # Standing Strikes
    "Jab": "jab",
    "Cross": "cross",
    "Hook": "hook",
    "Uppercut": "uppercut",
    "Kick": "kick",
    "Head Kick": "kick",
    "Body Kick": "kick",
    "Leg Kick": "kick",
    "Elbow": "elbow",
    "Knee": "knee",
    
    # SS Strikes (will be mapped based on metadata)
    "SS Jab": "ss_jab",
    "SS Cross": "ss_cross",
    "SS Hook": "ss_hook",
    "SS Uppercut": "ss_uppercut",
    "SS Kick": "ss_kick",
    "SS Elbow": "ss_elbow",
    "SS Knee": "ss_knee",
    
    # Damage
    "Rocked": "rocked",
    "Rocked/Stunned": "rocked",
    "KD": "kd_flash",  # Default, tier determines actual
    "KD Flash": "kd_flash",
    "KD Hard": "kd_hard",
    "KD Near-Finish": "kd_nf",
    "KD NF": "kd_nf",
    
    # Grappling
    "Takedown": "takedown",
    "TD": "takedown",
    "Takedown Landed": "takedown",
    "Takedown Stuffed": "takedown_stuffed",
    "Takedown Defended": "takedown_stuffed",
    "TD Stuffed": "takedown_stuffed",
    "TD Defended": "takedown_stuffed",
    
    # Ground Strikes
    "Ground Strike": "gnp_light",  # Default, quality determines actual
    "GnP Light": "gnp_light",
    "GnP Hard": "gnp_hard",
    "GnP Solid": "gnp_hard",
    
    # Control
    "Top Control": "top_control",
    "Ground Top Control": "top_control",
    "Back Control": "back_control",
    "Ground Back Control": "back_control",
    "Cage Control": "cage_control",
    "Cage Control Time": "cage_control",
    
    # Submissions
    "Submission Attempt": "sub_light",  # Default, tier determines actual
    "Sub Light": "sub_light",
    "Sub Deep": "sub_deep",
    "Sub Near-Finish": "sub_nf",
    "Sub NF": "sub_nf",
}


def get_all_event_configs():
    """Get flat dict of all event configurations"""
    all_events = {}
    for category in ["striking", "damage", "grappling", "ground_strikes", "submissions"]:
        if category in SCORING_CONFIG:
            all_events.update(SCORING_CONFIG[category])
    return all_events


def get_event_points(event_key: str) -> int:
    """Get base points for an event key"""
    all_events = get_all_event_configs()
    if event_key in all_events:
        return all_events[event_key].get("points", 0)
    # Check control separately
    if event_key in SCORING_CONFIG.get("control", {}):
        return SCORING_CONFIG["control"][event_key].get("points_per_bucket", 0)
    return 0


def get_control_config(control_key: str) -> dict:
    """Get control time configuration"""
    return SCORING_CONFIG.get("control", {}).get(control_key, {})


def is_ss_event(event_key: str) -> bool:
    """Check if event is a Significant Strike"""
    return event_key.startswith("ss_")


def is_protected_event(event_key: str) -> bool:
    """Check if event is protected (damage/impact)"""
    all_events = get_all_event_configs()
    return all_events.get(event_key, {}).get("is_protected", False)


def get_impact_lock(event_key: str) -> str:
    """Get impact lock type for an event (if any)"""
    all_events = get_all_event_configs()
    return all_events.get(event_key, {}).get("impact_lock", None)
