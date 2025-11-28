"""
Combat Sports Module

Manages sport types (MMA, Boxing, etc.) and sport-specific organizations.
"""

__version__ = "1.0.0"

# Sport type constants
SPORT_TYPES = {
    'mma': {
        'name': 'Mixed Martial Arts',
        'abbreviation': 'MMA',
        'scoring_categories': ['strikes', 'takedowns', 'submissions', 'control_time', 'knockdowns'],
        'positions': ['standing', 'clinch', 'ground'],
        'round_duration_seconds': 300,
        'organizations': ['ufc', 'bellator', 'one_championship', 'pfl', 'rizin', 'other']
    },
    'boxing': {
        'name': 'Boxing',
        'abbreviation': 'Boxing',
        'scoring_categories': ['punches', 'knockdowns'],
        'positions': ['standing'],
        'round_duration_seconds': 180,
        'organizations': ['wbc', 'wba', 'wbo', 'ibf', 'ring_magazine', 'other']
    },
    'dirty_boxing': {
        'name': 'Dirty Boxing',
        'abbreviation': 'Dirty Boxing',
        'scoring_categories': ['punches', 'elbows', 'clinch_strikes', 'knockdowns'],
        'positions': ['standing', 'clinch'],
        'round_duration_seconds': 180,
        'organizations': ['independent', 'other']
    },
    'bkfc': {
        'name': 'Bare Knuckle Fighting Championship',
        'abbreviation': 'BKFC',
        'scoring_categories': ['punches', 'knockdowns'],
        'positions': ['standing', 'clinch'],
        'round_duration_seconds': 120,
        'organizations': ['bkfc', 'gamebred_bareknuckle', 'other']
    },
    'karate_combat': {
        'name': 'Karate Combat',
        'abbreviation': 'Karate Combat',
        'scoring_categories': ['strikes', 'kicks', 'knockdowns'],
        'positions': ['standing'],
        'round_duration_seconds': 180,
        'organizations': ['karate_combat', 'other']
    },
    'other': {
        'name': 'Other Combat Sports',
        'abbreviation': 'Other',
        'scoring_categories': ['points'],
        'positions': ['standing'],
        'round_duration_seconds': 180,
        'organizations': ['independent', 'other']
    }
}
