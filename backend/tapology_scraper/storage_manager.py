"""
Storage Manager

Handles storage of scraped data with duplicate detection and batch processing.
"""

import logging
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage of scraped data in MongoDB"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
    
    async def store_fighter(self, fighter_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store fighter with duplicate detection
        
        Args:
            fighter_doc: Fighter document to store
            
        Returns:
            Result with status and fighter_id
        """
        try:
            # Check for existing fighter by Tapology ID
            tapology_id = fighter_doc.get('tapology_id')
            
            if tapology_id:
                existing = await self.db.fighters.find_one({'tapology_id': tapology_id})
                
                if existing:
                    # Update existing fighter
                    fighter_doc['updated_at'] = datetime.now(timezone.utc)
                    await self.db.fighters.update_one(
                        {'tapology_id': tapology_id},
                        {'$set': fighter_doc}
                    )
                    
                    logger.info(f"Updated existing fighter: {fighter_doc.get('name')}")
                    return {
                        'status': 'updated',
                        'fighter_id': existing.get('id'),
                        'tapology_id': tapology_id
                    }
            
            # Check by name if no Tapology ID match
            existing_by_name = await self.db.fighters.find_one({
                'name': fighter_doc.get('name'),
                'source': 'tapology'
            })
            
            if existing_by_name:
                # Update with Tapology ID if missing
                if tapology_id and not existing_by_name.get('tapology_id'):
                    fighter_doc['updated_at'] = datetime.now(timezone.utc)
                    await self.db.fighters.update_one(
                        {'id': existing_by_name['id']},
                        {'$set': {'tapology_id': tapology_id, 'tapology_url': fighter_doc.get('tapology_url')}}
                    )
                
                logger.info(f"Fighter already exists: {fighter_doc.get('name')}")
                return {
                    'status': 'exists',
                    'fighter_id': existing_by_name.get('id'),
                    'tapology_id': tapology_id
                }
            
            # Insert new fighter
            await self.db.fighters.insert_one(fighter_doc)
            logger.info(f"Inserted new fighter: {fighter_doc.get('name')}")
            
            return {
                'status': 'inserted',
                'fighter_id': fighter_doc['id'],
                'tapology_id': tapology_id
            }
            
        except Exception as e:
            logger.error(f"Error storing fighter: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def store_fighters_batch(self, fighters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store multiple fighters with batch processing
        
        Args:
            fighters: List of fighter documents
            
        Returns:
            Summary of storage operation
        """
        results = {
            'inserted': 0,
            'updated': 0,
            'exists': 0,
            'errors': 0,
            'fighters': []
        }
        
        for fighter in fighters:
            result = await self.store_fighter(fighter)
            results['fighters'].append(result)
            
            status = result.get('status')
            if status == 'inserted':
                results['inserted'] += 1
            elif status == 'updated':
                results['updated'] += 1
            elif status == 'exists':
                results['exists'] += 1
            elif status == 'error':
                results['errors'] += 1
        
        logger.info(f"Batch stored {len(fighters)} fighters: {results['inserted']} inserted, {results['updated']} updated, {results['exists']} existed")
        return results
    
    async def store_event_summary(self, event_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store event summary data
        
        Args:
            event_doc: Event document
            
        Returns:
            Storage result
        """
        try:
            tapology_id = event_doc.get('tapology_id')
            
            # Check for existing event
            if tapology_id:
                existing = await self.db.tapology_events.find_one({'tapology_id': tapology_id})
                
                if existing:
                    logger.info(f"Event already exists: {event_doc.get('event_name')}")
                    return {
                        'status': 'exists',
                        'event_name': event_doc.get('event_name'),
                        'tapology_id': tapology_id
                    }
            
            # Insert new event
            await self.db.tapology_events.insert_one(event_doc)
            logger.info(f"Inserted event: {event_doc.get('event_name')}")
            
            return {
                'status': 'inserted',
                'event_name': event_doc.get('event_name'),
                'tapology_id': tapology_id
            }
            
        except Exception as e:
            logger.error(f"Error storing event: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def store_fight_stats(self, fight_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store fight statistics
        
        Args:
            fight_stats: List of fight_stats documents
            
        Returns:
            Storage summary
        """
        try:
            if not fight_stats:
                return {'status': 'success', 'inserted': 0}
            
            # Insert fight stats
            result = await self.db.fight_stats.insert_many(fight_stats)
            
            logger.info(f"Inserted {len(result.inserted_ids)} fight stats")
            return {
                'status': 'success',
                'inserted': len(result.inserted_ids)
            }
            
        except Exception as e:
            logger.error(f"Error storing fight stats: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def get_scraping_status(self) -> Dict[str, Any]:
        """
        Get status of scraped data
        
        Returns:
            Statistics about scraped data
        """
        try:
            tapology_fighters = await self.db.fighters.count_documents({'source': 'tapology'})
            tapology_events = await self.db.tapology_events.count_documents({})
            
            # Get recent scrapes
            recent_fighters = await self.db.fighters.find(
                {'source': 'tapology'}
            ).sort('created_at', -1).limit(5).to_list(length=5)
            
            recent_events = await self.db.tapology_events.find().sort(
                'scraped_at', -1
            ).limit(5).to_list(length=5)
            
            return {
                'total_fighters_scraped': tapology_fighters,
                'total_events_scraped': tapology_events,
                'recent_fighters': [
                    {
                        'name': f.get('name'),
                        'record': f.get('record'),
                        'scraped': f.get('created_at', '').isoformat() if isinstance(f.get('created_at'), datetime) else f.get('created_at')
                    }
                    for f in recent_fighters
                ],
                'recent_events': [
                    {
                        'event_name': e.get('event_name'),
                        'fight_count': e.get('fight_count'),
                        'scraped': e.get('scraped_at')
                    }
                    for e in recent_events
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting scraping status: {e}")
            return {'error': str(e)}
    
    async def find_fighter_by_tapology_id(self, tapology_id: str) -> Optional[Dict[str, Any]]:
        """Find fighter by Tapology ID"""
        try:
            fighter = await self.db.fighters.find_one({'tapology_id': tapology_id})
            return fighter
        except Exception as e:
            logger.error(f"Error finding fighter: {e}")
            return None
    
    async def search_fighters(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for fighters by name
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching fighters
        """
        try:
            # Case-insensitive regex search
            regex_pattern = f".*{query}.*"
            fighters = await self.db.fighters.find(
                {
                    'name': {'$regex': regex_pattern, '$options': 'i'},
                    'source': 'tapology'
                }
            ).limit(limit).to_list(length=limit)
            
            return fighters
            
        except Exception as e:
            logger.error(f"Error searching fighters: {e}")
            return []
