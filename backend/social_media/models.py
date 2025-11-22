"""
Social Media Integration - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid

class SocialPost(BaseModel):
    """Social media post"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: Literal["twitter", "instagram", "facebook"]
    content: str
    media_url: Optional[str] = None
    hashtags: list[str] = Field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    posted: bool = False
    post_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RoundScorePost(BaseModel):
    """Auto-generated round score post"""
    bout_id: str
    round_num: int
    fighter_1_name: str
    fighter_1_score: int
    fighter_2_name: str
    fighter_2_score: int
    template: str = "Round {round_num} Scores:\n{fighter_1}: {score_1}\n{fighter_2}: {score_2}"
