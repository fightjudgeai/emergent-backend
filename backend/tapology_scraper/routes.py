"""
Tapology Scraper API Routes

REST endpoints for triggering and managing web scraping operations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging
from datetime import datetime, timezone

from .scraper_engine import TapologyScraper
from .data_transformer import DataTransformer
from .storage_manager import StorageManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraper", tags=["Tapology Scraper"])

# Global instances (initialized in server.py)
db: Optional[AsyncIOMotorDatabase] = None
scraper: Optional[TapologyScraper] = None
storage: Optional[StorageManager] = None

# Scraping status tracking
scraping_status = {
    'is_running': False,
    'current_operation': None,
    'last_run': None,
    'last_result': None
}


def init_tapology_scraper(database: AsyncIOMotorDatabase):
    """Initialize the scraper with database connection"""
    global db, scraper, storage
    db = database
    scraper = TapologyScraper()
    storage = StorageManager(database)
    logger.info("✅ Tapology Scraper initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Tapology Scraper",
        "version": "1.0.0",
        "status": "operational",
        "scraper_active": scraper is not None,
        "storage_active": storage is not None
    }


@router.get("/status")
async def get_scraping_status():
    """
    Get current scraping status and statistics
    
    Returns:
    - Current operation status
    - Total scraped data counts
    - Recent scrapes
    """
    
    if not storage:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    
    try:
        stats = await storage.get_scraping_status()
        
        return {
            **scraping_status,
            'statistics': stats
        }
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/recent")
async def scrape_recent_events(
    background_tasks: BackgroundTasks,
    limit: int = 20
):
    """
    Scrape recent MMA events from Tapology
    
    Args:
        limit: Maximum number of events to scrape (default: 20)
    
    Returns:
        Scraping job status
    """
    
    if not scraper or not storage:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    if scraping_status['is_running']:
        raise HTTPException(status_code=429, detail="Scraping operation already in progress")
    
    # Start background task
    background_tasks.add_task(_scrape_events_task, limit)
    
    return {
        "status": "started",
        "operation": "scrape_recent_events",
        "limit": limit,
        "message": f"Started scraping up to {limit} recent events"
    }


async def _scrape_events_task(limit: int):
    """Background task for scraping events"""
    global scraping_status
    
    try:
        scraping_status['is_running'] = True
        scraping_status['current_operation'] = f"Scraping {limit} recent events"
        
        # Scrape events
        events_data = scraper.scrape_recent_events(limit=limit)
        
        # Transform and store
        results = {
            'events_scraped': len(events_data),
            'events_stored': 0,
            'fighters_discovered': 0,
            'fighters_stored': 0
        }
        
        for event_data in events_data:
            # Store event summary
            event_doc = DataTransformer.transform_event(event_data)
            if event_doc:
                await storage.store_event_summary(event_doc)
                results['events_stored'] += 1
            
            # Extract and store fighters from event
            for fight in event_data.get('fights', []):
                for fighter_key in ['fighter1', 'fighter2']:
                    fighter_data = fight.get(fighter_key)
                    if fighter_data and fighter_data.get('tapology_id'):
                        # Scrape full fighter profile
                        fighter_profile = scraper.scrape_fighter_profile(fighter_data['tapology_id'])
                        if fighter_profile:
                            fighter_doc = DataTransformer.transform_fighter(fighter_profile)
                            if fighter_doc:
                                result = await storage.store_fighter(fighter_doc)
                                if result.get('status') == 'inserted':
                                    results['fighters_stored'] += 1
                                results['fighters_discovered'] += 1
        
        scraping_status['last_result'] = results
        scraping_status['last_run'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Event scraping completed: {results}")
        
    except Exception as e:
        logger.error(f"Error in event scraping task: {e}")
        scraping_status['last_result'] = {'error': str(e)}
    
    finally:
        scraping_status['is_running'] = False
        scraping_status['current_operation'] = None


@router.post("/fighter/{fighter_identifier}")
async def scrape_fighter(fighter_identifier: str):
    """
    Scrape specific fighter by name or Tapology ID
    
    Args:
        fighter_identifier: Fighter name or Tapology ID
    
    Returns:
        Scraped fighter data
    """
    
    if not scraper or not storage:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    try:
        # Determine if identifier is Tapology ID (numeric) or name
        if fighter_identifier.isdigit():
            fighter_id = fighter_identifier
        else:
            # Search for fighter by name
            fighter_id = scraper.search_fighter(fighter_identifier)
            if not fighter_id:
                raise HTTPException(status_code=404, detail=f"Fighter '{fighter_identifier}' not found on Tapology")
        
        # Scrape fighter profile
        fighter_data = scraper.scrape_fighter_profile(fighter_id)
        
        if not fighter_data:
            raise HTTPException(status_code=404, detail="Failed to scrape fighter data")
        
        # Transform and store
        fighter_doc = DataTransformer.transform_fighter(fighter_data)
        if not fighter_doc:
            raise HTTPException(status_code=500, detail="Failed to transform fighter data")
        
        result = await storage.store_fighter(fighter_doc)
        
        return {
            "status": "success",
            "fighter": {
                "id": result.get('fighter_id'),
                "tapology_id": result.get('tapology_id'),
                "name": fighter_doc.get('name'),
                "record": fighter_doc.get('record'),
                "storage_status": result.get('status')
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scraping fighter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/event/{event_id}")
async def scrape_event_details(event_id: str):
    """
    Scrape detailed event information including fight card
    
    Args:
        event_id: Tapology event ID
    
    Returns:
        Event details with fights
    """
    
    if not scraper or not storage:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    try:
        # Scrape event
        event_data = scraper.scrape_event_details(event_id)
        
        if not event_data:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found or failed to scrape")
        
        # Transform and store
        event_doc = DataTransformer.transform_event(event_data)
        if event_doc:
            await storage.store_event_summary(event_doc)
        
        # Store fighters from fights
        fighters_stored = 0
        for fight in event_data.get('fights', []):
            for fighter_key in ['fighter1', 'fighter2']:
                fighter_data = fight.get(fighter_key)
                if fighter_data and fighter_data.get('tapology_id'):
                    # Check if fighter already exists
                    existing = await storage.find_fighter_by_tapology_id(fighter_data['tapology_id'])
                    if not existing:
                        # Scrape full profile
                        fighter_profile = scraper.scrape_fighter_profile(fighter_data['tapology_id'])
                        if fighter_profile:
                            fighter_doc = DataTransformer.transform_fighter(fighter_profile)
                            if fighter_doc:
                                await storage.store_fighter(fighter_doc)
                                fighters_stored += 1
        
        return {
            "status": "success",
            "event": {
                "name": event_data.get('event_name'),
                "tapology_id": event_id,
                "fights_count": len(event_data.get('fights', [])),
                "fighters_stored": fighters_stored
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scraping event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/ufc-recent")
async def scrape_ufc_recent(background_tasks: BackgroundTasks, limit: int = 10):
    """
    Scrape recent UFC events specifically
    
    Args:
        limit: Number of UFC events to scrape
    
    Returns:
        Job status
    """
    
    if not scraper or not storage:
        raise HTTPException(status_code=500, detail="Scraper not initialized")
    
    if scraping_status['is_running']:
        raise HTTPException(status_code=429, detail="Scraping operation already in progress")
    
    # Note: This is a simplified version. A full implementation would filter for UFC events
    background_tasks.add_task(_scrape_events_task, limit)
    
    return {
        "status": "started",
        "operation": "scrape_ufc_recent",
        "limit": limit,
        "message": f"Started scraping up to {limit} recent UFC events"
    }


@router.get("/fighters/search")
async def search_fighters(query: str, limit: int = 10):
    """
    Search for fighters in database
    
    Args:
        query: Search query (fighter name)
        limit: Maximum results
    
    Returns:
        List of matching fighters
    """
    
    if not storage:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    
    try:
        fighters = await storage.search_fighters(query, limit)
        
        return {
            "query": query,
            "count": len(fighters),
            "fighters": [
                {
                    "id": f.get('id'),
                    "name": f.get('name'),
                    "record": f.get('record'),
                    "tapology_id": f.get('tapology_id'),
                    "weight_class": f.get('weight_class')
                }
                for f in fighters
            ]
        }
    
    except Exception as e:
        logger.error(f"Error searching fighters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
