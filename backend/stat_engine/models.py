"""
Stat Engine Data Models

Database schemas for aggregated statistics.
All stats are derived from the events table.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid


class RoundStats(BaseModel):
    """Per-round statistics for a fighter"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fight_id: str
    round_num: int
    fighter_id: str
    
    # Strike Statistics
    total_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    
    # Significant Strike Breakdown
    sig_head_landed: int = 0
    sig_body_landed: int = 0
    sig_leg_landed: int = 0
    
    # Power Strikes
    knockdowns: int = 0
    rocked_events: int = 0
    
    # Takedown Statistics
    td_attempts: int = 0
    td_landed: int = 0
    td_stuffed: int = 0
    
    # Submission Attempts
    sub_attempts: int = 0
    
    # Control Time (seconds)
    ground_control_secs: int = 0
    clinch_control_secs: int = 0
    cage_control_secs: int = 0
    back_control_secs: int = 0
    mount_secs: int = 0
    
    # Total Control
    total_control_secs: int = 0
    
    # Metadata
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_event_count: int = 0  # Number of events processed
    
    class Config:
        json_schema_extra = {
            "example": {
                "fight_id": "ufc301_main",
                "round_num": 1,
                "fighter_id": "fighter_1",
                "sig_strikes_landed": 15,
                "knockdowns": 1,
                "total_control_secs": 120
            }
        }


class FightStats(BaseModel):
    """Aggregated statistics for entire fight"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fight_id: str
    fighter_id: str
    
    # Fight Metadata
    total_rounds: int = 0
    
    # Aggregated Strike Statistics
    total_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    
    # Significant Strike Breakdown
    sig_head_landed: int = 0
    sig_body_landed: int = 0
    sig_leg_landed: int = 0
    
    # Power Strikes
    knockdowns: int = 0
    rocked_events: int = 0
    
    # Takedown Statistics
    td_attempts: int = 0
    td_landed: int = 0
    td_stuffed: int = 0
    
    # Submission Attempts
    sub_attempts: int = 0
    
    # Control Time (seconds)
    ground_control_secs: int = 0
    clinch_control_secs: int = 0
    cage_control_secs: int = 0
    back_control_secs: int = 0
    mount_secs: int = 0
    total_control_secs: int = 0
    
    # Computed Metrics
    sig_strike_accuracy: float = 0.0  # percentage
    td_accuracy: float = 0.0  # percentage
    strikes_per_minute: float = 0.0
    control_time_percentage: float = 0.0  # of total fight time
    
    # Metadata
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rounds_aggregated: int = 0


class CareerStats(BaseModel):
    """Career-wide statistics for a fighter"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fighter_id: str
    
    # Career Summary
    total_fights: int = 0
    total_rounds: int = 0
    
    # Aggregated Lifetime Statistics
    total_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    
    sig_head_landed: int = 0
    sig_body_landed: int = 0
    sig_leg_landed: int = 0
    
    knockdowns: int = 0
    rocked_events: int = 0
    
    td_attempts: int = 0
    td_landed: int = 0
    td_stuffed: int = 0
    
    sub_attempts: int = 0
    
    # Total Control Time
    ground_control_secs: int = 0
    clinch_control_secs: int = 0
    cage_control_secs: int = 0
    back_control_secs: int = 0
    mount_secs: int = 0
    total_control_secs: int = 0
    
    # Advanced Career Metrics
    avg_sig_strikes_per_min: float = 0.0
    avg_sig_strike_accuracy: float = 0.0
    avg_td_accuracy: float = 0.0
    avg_control_time_per_fight: float = 0.0  # seconds
    knockdowns_per_15min: float = 0.0
    td_defense_percentage: float = 0.0
    
    # Metadata
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fights_aggregated: int = 0


class AggregationJob(BaseModel):
    """Track aggregation job execution"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str  # 'round', 'fight', 'career', 'manual'
    trigger: str  # 'manual', 'round_locked', 'post_fight', 'nightly'
    
    # Scope
    fight_id: Optional[str] = None
    round_num: Optional[int] = None
    fighter_id: Optional[str] = None
    
    # Execution
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    rows_processed: int = 0
    rows_updated: int = 0
    errors: List[str] = []
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatEngineHealth(BaseModel):
    """Health check response"""
    
    service: str = "Stat Engine"
    version: str = "1.0.0"
    status: str = "operational"
    
    # System Status
    event_reader_active: bool = True
    aggregation_active: bool = True
    scheduler_active: bool = True
    
    # Database Status
    round_stats_count: int = 0
    fight_stats_count: int = 0
    career_stats_count: int = 0
    
    # Recent Activity
    last_aggregation: Optional[datetime] = None
    pending_jobs: int = 0
