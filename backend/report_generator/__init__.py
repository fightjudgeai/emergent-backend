"""
Report Generator Service
Generate comprehensive fight reports in PDF/HTML/JSON
"""

from .generator_engine import ReportGeneratorEngine
from .routes import report_generator_api

__version__ = "1.0.0"
