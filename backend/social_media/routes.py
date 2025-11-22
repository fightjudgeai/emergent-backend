"""
Social Media Integration - API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .social_engine import SocialMediaEngine
from .models import SocialPost, RoundScorePost

logger = logging.getLogger(__name__)

social_media_api = APIRouter(tags=["Social Media"])
social_engine: Optional[SocialMediaEngine] = None

def get_social_engine():
    if social_engine is None:
        raise HTTPException(status_code=500, detail="Social media engine not initialized")
    return social_engine

@social_media_api.post("/social/twitter/post", response_model=SocialPost)
async def post_to_twitter(content: str, media_url: Optional[str] = None):
    """Post to Twitter"""
    engine = get_social_engine()
    return await engine.post_to_twitter(content, media_url)

@social_media_api.post("/social/instagram/story")
async def post_instagram_story(story_data: dict):
    """Post Instagram story"""
    engine = get_social_engine()
    return await engine.post_to_instagram(story_data)

@social_media_api.post("/social/auto/round-score")
async def auto_post_round_score(data: RoundScorePost):
    """Auto-post round scores to all platforms"""
    engine = get_social_engine()
    return await engine.auto_post_round_score(data)

@social_media_api.get("/social/posts")
async def get_posts():
    """Get recent social media posts"""
    engine = get_social_engine()
    return {"posts": engine.posts_cache, "count": len(engine.posts_cache)}

@social_media_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Social Media Integration", "version": "1.0.0"}
