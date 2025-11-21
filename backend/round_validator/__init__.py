"""
Round Validator Service
Validate rounds before scoring and locking
"""

from .validator_engine import RoundValidatorEngine
from .routes import round_validator_api

__version__ = "1.0.0"
