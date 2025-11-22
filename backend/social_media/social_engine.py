"""
Social Media Integration - Engine
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from .models import SocialPost, RoundScorePost

logger = logging.getLogger(__name__)

class SocialMediaEngine:
    """Social media auto-posting engine"""
    
    def __init__(self, db=None):
        self.db = db
        self.posts_cache = []
    
    def generate_round_score_tweet(self, data: RoundScorePost) -> str:
        """Generate tweet text for round scores"""
        text = f"🥊 Round {data.round_num} Scores\n\n"
        text += f"{data.fighter_1_name}: {data.fighter_1_score}\n"
        text += f"{data.fighter_2_name}: {data.fighter_2_score}\n\n"
        text += f"#MMA #Boxing #FightScores #Round{data.round_num}"
        return text
    
    def generate_instagram_story_data(self, data: RoundScorePost) -> dict:
        """Generate Instagram story data"""
        return {
            "type": "story",
            "background_color": "#000000",
            "text_elements": [
                {"text": f"ROUND {data.round_num}", "size": "large", "y": 100},
                {"text": data.fighter_1_name, "size": "medium", "y": 400},
                {"text": str(data.fighter_1_score), "size": "xlarge", "y": 500},
                {"text": "VS", "size": "small", "y": 650},
                {"text": data.fighter_2_name, "size": "medium", "y": 800},
                {"text": str(data.fighter_2_score), "size": "xlarge", "y": 900}
            ]
        }
    
    async def post_to_twitter(self, content: str, media_url: Optional[str] = None) -> SocialPost:
        """Post to Twitter (simulated)"""
        post = SocialPost(
            platform="twitter",
            content=content,
            media_url=media_url,
            posted=True,
            post_id=f"tweet_{datetime.now().timestamp()}"
        )
        
        self.posts_cache.append(post)
        logger.info(f"Posted to Twitter: {content[:50]}...")
        
        if self.db is not None:
            try:
                post_dict = post.model_dump()
                post_dict['created_at'] = post_dict['created_at'].isoformat()
                await self.db.social_posts.insert_one(post_dict)
            except Exception as e:
                logger.error(f"Error storing post: {e}")
        
        return post
    
    async def post_to_instagram(self, story_data: dict) -> SocialPost:
        """Post Instagram story (simulated)"""
        post = SocialPost(
            platform="instagram",
            content="Story posted",
            posted=True,
            post_id=f"story_{datetime.now().timestamp()}"
        )
        
        self.posts_cache.append(post)
        logger.info("Posted Instagram story")
        
        if self.db is not None:
            try:
                post_dict = post.model_dump()
                post_dict['created_at'] = post_dict['created_at'].isoformat()
                await self.db.social_posts.insert_one(post_dict)
            except Exception as e:
                logger.error(f"Error storing post: {e}")
        
        return post
    
    async def auto_post_round_score(self, data: RoundScorePost) -> dict:
        """Auto-post round scores to all platforms"""
        results = {}
        
        # Twitter
        tweet_text = self.generate_round_score_tweet(data)
        twitter_post = await self.post_to_twitter(tweet_text)
        results["twitter"] = twitter_post
        
        # Instagram
        story_data = self.generate_instagram_story_data(data)
        instagram_post = await self.post_to_instagram(story_data)
        results["instagram"] = instagram_post
        
        return results
