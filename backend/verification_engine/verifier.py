"""
Verification Engine

Compares stats across multiple data sources and flags discrepancies.
"""

import logging
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class VerificationEngine:
    """Multi-operator verification for data accuracy"""
    
    # Thresholds for flagging discrepancies
    SIG_STRIKES_THRESHOLD_PERCENT = 10  # 10% difference
    TAKEDOWN_THRESHOLD = 1  # 1 takedown difference
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
    
    async def verify_round(self, fight_id: str, round_num: int) -> Dict[str, Any]:
        """
        Verify round stats across all sources
        
        Args:
            fight_id: Fight identifier
            round_num: Round number
            
        Returns:
            Verification result with flags
        """
        try:
            # Get round stats from all sources
            all_round_stats = await self.db.round_stats.find({
                'fight_id': fight_id,
                'round': round_num
            }).to_list(length=100)
            
            if not all_round_stats:
                return {
                    'status': 'no_data',
                    'fight_id': fight_id,
                    'round': round_num
                }
            
            # Group by fighter and source
            stats_by_fighter = {}
            
            for stat in all_round_stats:
                fighter_id = stat.get('fighter_id')
                source = stat.get('source', 'unknown')
                
                if fighter_id not in stats_by_fighter:
                    stats_by_fighter[fighter_id] = {}
                
                stats_by_fighter[fighter_id][source] = stat
            
            # Compare across sources for each fighter
            discrepancies = []
            
            for fighter_id, sources in stats_by_fighter.items():
                fighter_discrepancies = self._compare_sources(fighter_id, sources, fight_id, round_num)
                if fighter_discrepancies:
                    discrepancies.extend(fighter_discrepancies)
            
            # Store discrepancies
            if discrepancies:
                await self._store_discrepancies(discrepancies)
            
            return {
                'status': 'verified',
                'fight_id': fight_id,
                'round': round_num,
                'discrepancies_found': len(discrepancies),
                'discrepancies': discrepancies,
                'requires_review': len(discrepancies) > 0
            }
            
        except Exception as e:
            logger.error(f"Error verifying round: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _compare_sources(
        self,
        fighter_id: str,
        sources: Dict[str, Dict[str, Any]],
        fight_id: str,
        round_num: int
    ) -> List[Dict[str, Any]]:
        """Compare stats across multiple sources for a fighter"""
        
        discrepancies = []
        source_names = list(sources.keys())
        
        # Need at least 2 sources to compare
        if len(source_names) < 2:
            return discrepancies
        
        # Compare all pairs of sources
        for i in range(len(source_names)):
            for j in range(i + 1, len(source_names)):
                source1 = source_names[i]
                source2 = source_names[j]
                
                stats1 = sources[source1]
                stats2 = sources[source2]
                
                # Compare significant strikes
                sig_strikes_discrepancy = self._check_sig_strikes_discrepancy(
                    stats1, stats2, source1, source2, fighter_id, fight_id, round_num
                )
                if sig_strikes_discrepancy:
                    discrepancies.append(sig_strikes_discrepancy)
                
                # Compare takedowns
                td_discrepancy = self._check_takedown_discrepancy(
                    stats1, stats2, source1, source2, fighter_id, fight_id, round_num
                )
                if td_discrepancy:
                    discrepancies.append(td_discrepancy)
        
        return discrepancies
    
    def _check_sig_strikes_discrepancy(
        self,
        stats1: Dict[str, Any],
        stats2: Dict[str, Any],
        source1: str,
        source2: str,
        fighter_id: str,
        fight_id: str,
        round_num: int
    ) -> Optional[Dict[str, Any]]:
        """Check for significant strikes discrepancy (>10%)"""
        
        sig_strikes1 = stats1.get('significant_strikes', 0)
        sig_strikes2 = stats2.get('significant_strikes', 0)
        
        # Calculate percentage difference
        if sig_strikes1 == 0 and sig_strikes2 == 0:
            return None
        
        avg = (sig_strikes1 + sig_strikes2) / 2
        if avg == 0:
            return None
        
        diff = abs(sig_strikes1 - sig_strikes2)
        percent_diff = (diff / avg) * 100
        
        if percent_diff > self.SIG_STRIKES_THRESHOLD_PERCENT:
            return {
                'discrepancy_id': str(uuid.uuid4()),
                'fight_id': fight_id,
                'round': round_num,
                'fighter_id': fighter_id,
                'metric': 'significant_strikes',
                'source1': source1,
                'source2': source2,
                'value1': sig_strikes1,
                'value2': sig_strikes2,
                'difference': diff,
                'percent_difference': round(percent_diff, 2),
                'severity': 'high' if percent_diff > 20 else 'medium',
                'flagged_at': datetime.now(timezone.utc),
                'status': 'pending_review'
            }
        
        return None
    
    def _check_takedown_discrepancy(
        self,
        stats1: Dict[str, Any],
        stats2: Dict[str, Any],
        source1: str,
        source2: str,
        fighter_id: str,
        fight_id: str,
        round_num: int
    ) -> Optional[Dict[str, Any]]:
        """Check for takedown discrepancy (>1 difference)"""
        
        tds1 = stats1.get('takedowns', 0)
        tds2 = stats2.get('takedowns', 0)
        
        diff = abs(tds1 - tds2)
        
        if diff > self.TAKEDOWN_THRESHOLD:
            return {
                'discrepancy_id': str(uuid.uuid4()),
                'fight_id': fight_id,
                'round': round_num,
                'fighter_id': fighter_id,
                'metric': 'takedowns',
                'source1': source1,
                'source2': source2,
                'value1': tds1,
                'value2': tds2,
                'difference': diff,
                'severity': 'high' if diff > 2 else 'medium',
                'flagged_at': datetime.now(timezone.utc),
                'status': 'pending_review'
            }
        
        return None
    
    async def _store_discrepancies(self, discrepancies: List[Dict[str, Any]]):
        """Store discrepancies in database"""
        try:
            if discrepancies:
                await self.db.stat_discrepancies.insert_many(discrepancies)
                logger.info(f"Stored {len(discrepancies)} discrepancies")
        except Exception as e:
            logger.error(f"Error storing discrepancies: {e}")
    
    async def get_discrepancies(
        self,
        fight_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get discrepancies with filters
        
        Args:
            fight_id: Filter by fight
            status: Filter by status (pending_review, reviewed, resolved)
            severity: Filter by severity (high, medium, low)
            limit: Maximum results
            
        Returns:
            List of discrepancies
        """
        try:
            query = {}
            
            if fight_id:
                query['fight_id'] = fight_id
            
            if status:
                query['status'] = status
            
            if severity:
                query['severity'] = severity
            
            discrepancies = await self.db.stat_discrepancies.find(
                query
            ).sort('flagged_at', -1).limit(limit).to_list(length=limit)
            
            return discrepancies
            
        except Exception as e:
            logger.error(f"Error getting discrepancies: {e}")
            return []
    
    async def resolve_discrepancy(
        self,
        discrepancy_id: str,
        resolution: str,
        resolved_by: str
    ) -> bool:
        """
        Resolve a discrepancy
        
        Args:
            discrepancy_id: Discrepancy ID
            resolution: Resolution notes
            resolved_by: User who resolved it
            
        Returns:
            Success status
        """
        try:
            result = await self.db.stat_discrepancies.update_one(
                {'discrepancy_id': discrepancy_id},
                {
                    '$set': {
                        'status': 'resolved',
                        'resolution': resolution,
                        'resolved_by': resolved_by,
                        'resolved_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error resolving discrepancy: {e}")
            return False
