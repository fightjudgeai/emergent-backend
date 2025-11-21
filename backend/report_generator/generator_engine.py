"""
Report Generator - Main Engine
"""

import json
from typing import Dict, List
import logging
import sys
sys.path.append('/app/backend')
from .models import FightReport, ReportFormat, RoundScore, MajorEvent

logger = logging.getLogger(__name__)


class ReportGeneratorEngine:
    """Generate fight reports"""
    
    def generate_report(self, report_data: FightReport, format: ReportFormat) -> str:
        """
        Generate report in specified format
        
        Args:
            report_data: Report data
            format: Output format
        
        Returns:
            Report content as string
        """
        if format == ReportFormat.JSON:
            return self._generate_json(report_data)
        elif format == ReportFormat.HTML:
            return self._generate_html(report_data)
        elif format == ReportFormat.PDF:
            return self._generate_pdf_placeholder(report_data)
        
        return ""
    
    def _generate_json(self, report: FightReport) -> str:
        """Generate JSON report"""
        return report.model_dump_json(indent=2)
    
    def _generate_html(self, report: FightReport) -> str:
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fight Report - {report.bout_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #1a1d24; color: white; padding: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ccc; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Fight Report</h1>
                <p>{report.event_name} - {report.bout_id}</p>
            </div>
            
            <div class="section">
                <h2>Round Scores</h2>
                <table>
                    <tr><th>Round</th><th>AI Score</th><th>Winner</th><th>Confidence</th></tr>
                    {''.join(f'<tr><td>{r.round_num}</td><td>{r.ai_composite_score}</td><td>{r.winner}</td><td>{r.confidence:.0%}</td></tr>' for r in report.round_scores)}
                </table>
            </div>
            
            <div class="section">
                <h2>Major Events ({len(report.major_events)})</h2>
                <table>
                    <tr><th>Time</th><th>Type</th><th>Fighter</th><th>Severity</th></tr>
                    {''.join(f'<tr><td>{e.timestamp_ms/1000:.1f}s</td><td>{e.event_type}</td><td>{e.fighter_id}</td><td>{e.severity:.1f}</td></tr>' for e in report.major_events[:20])}
                </table>
            </div>
            
            <div class="section">
                <h2>Model Versions</h2>
                <p>{'<br>'.join(f'{k}: {v}' for k, v in report.model_versions.items())}</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_pdf_placeholder(self, report: FightReport) -> str:
        """Generate PDF (placeholder - would use reportlab in production)"""
        return f"PDF Report for {report.bout_id} - Use reportlab library for actual PDF generation"
