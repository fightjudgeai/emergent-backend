"""
Market Settlement Engine
Handles sportsbook market settlement with automatic and manual triggers
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class MarketType(str, Enum):
    """Supported market types"""
    WINNER = "WINNER"
    TOTAL_SIG_STRIKES = "TOTAL_SIG_STRIKES"
    KD_OVER_UNDER = "KD_OVER_UNDER"
    SUB_ATT_OVER_UNDER = "SUB_ATT_OVER_UNDER"


class MarketStatus(str, Enum):
    """Market status values"""
    OPEN = "OPEN"
    SUSPENDED = "SUSPENDED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


class MarketSettler:
    """
    Market settlement engine for sportsbook markets
    
    Auto-settles markets when fight ends using:
    - fight_results for WINNER markets
    - round_state (latest) for stat-based markets
    """
    
    def __init__(self, db_client):
        self.db = db_client
    
    def create_market(
        self,
        fight_id: UUID,
        market_type: MarketType,
        params: Dict[str, Any],
        status: MarketStatus = MarketStatus.OPEN
    ) -> Dict:
        """
        Create a new market
        
        Args:
            fight_id: Fight UUID
            market_type: Type of market (WINNER, TOTAL_SIG_STRIKES, etc.)
            params: Market parameters (e.g., {"line": 50.5, "over_odds": 1.91})
            status: Initial status (default: OPEN)
        
        Returns:
            Created market record
        """
        try:
            response = self.db.client.table('markets')\
                .insert({
                    'fight_id': str(fight_id),
                    'market_type': market_type.value,
                    'params': params,
                    'status': status.value
                })\
                .execute()
            
            if response.data:
                logger.info(f"Created market: {market_type.value} for fight {fight_id}")
                return response.data[0]
            else:
                raise Exception("No data returned from insert")
        
        except Exception as e:
            logger.error(f"Error creating market: {e}")
            raise
    
    def get_market(self, market_id: UUID) -> Optional[Dict]:
        """Get market by ID"""
        response = self.db.client.table('markets')\
            .select('*')\
            .eq('id', str(market_id))\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_fight_markets(
        self,
        fight_id: UUID,
        status: Optional[MarketStatus] = None
    ) -> List[Dict]:
        """Get all markets for a fight"""
        query = self.db.client.table('markets')\
            .select('*')\
            .eq('fight_id', str(fight_id))
        
        if status:
            query = query.eq('status', status.value)
        
        response = query.execute()
        return response.data if response.data else []
    
    def update_market_status(
        self,
        market_id: UUID,
        status: MarketStatus
    ) -> Dict:
        """Update market status"""
        response = self.db.client.table('markets')\
            .update({'status': status.value})\
            .eq('id', str(market_id))\
            .execute()
        
        return response.data[0] if response.data else None
    
    def settle_market(self, market_id: UUID) -> Dict[str, Any]:
        """
        Settle a market using SQL function
        
        Calls the database settle_market() function which:
        - Routes to appropriate settlement logic based on market_type
        - Inserts settlement record
        - Updates market status to SETTLED
        
        Args:
            market_id: Market UUID
        
        Returns:
            Settlement result with details
        """
        try:
            # Call SQL settlement function
            result = self.db.client.rpc(
                'settle_market',
                {'p_market_id': str(market_id)}
            ).execute()
            
            if result.data:
                settlement = result.data[0] if isinstance(result.data, list) else result.data
                logger.info(f"Settled market {market_id}: {settlement.get('market_type')}")
                return {
                    'success': True,
                    'market_id': str(market_id),
                    'settlement': settlement
                }
            else:
                raise Exception("No settlement data returned")
        
        except Exception as e:
            logger.error(f"Error settling market {market_id}: {e}")
            return {
                'success': False,
                'market_id': str(market_id),
                'error': str(e)
            }
    
    def settle_winner_market(
        self,
        fight_id: UUID,
        winner_side: str,
        method: str,
        round_num: int,
        time: str
    ) -> Dict[str, Any]:
        """
        Manually settle WINNER market
        
        Alternative to auto-settlement, uses provided fight result data
        """
        result_payload = {
            'market_type': 'WINNER',
            'winner_side': winner_side,
            'method': method,
            'round': round_num,
            'time': time
        }
        
        return result_payload
    
    def settle_total_sig_strikes_market(
        self,
        fight_id: UUID,
        line: float
    ) -> Dict[str, Any]:
        """
        Manually settle TOTAL_SIG_STRIKES market
        
        Gets latest round_state and calculates total
        """
        # Get latest round state
        round_states = self.db.get_round_states(fight_id)
        
        if not round_states:
            raise Exception(f"No round states found for fight {fight_id}")
        
        latest = max(round_states, key=lambda r: r['seq'])
        
        total_sig_strikes = latest['red_sig_strikes'] + latest['blue_sig_strikes']
        over_wins = total_sig_strikes > line
        
        result_payload = {
            'market_type': 'TOTAL_SIG_STRIKES',
            'line': line,
            'actual_total': total_sig_strikes,
            'red_sig_strikes': latest['red_sig_strikes'],
            'blue_sig_strikes': latest['blue_sig_strikes'],
            'winning_side': 'OVER' if over_wins else 'UNDER'
        }
        
        return result_payload
    
    def settle_kd_over_under_market(
        self,
        fight_id: UUID,
        line: float
    ) -> Dict[str, Any]:
        """Manually settle KD_OVER_UNDER market"""
        # Get latest round state
        round_states = self.db.get_round_states(fight_id)
        
        if not round_states:
            raise Exception(f"No round states found for fight {fight_id}")
        
        latest = max(round_states, key=lambda r: r['seq'])
        
        total_knockdowns = latest['red_knockdowns'] + latest['blue_knockdowns']
        over_wins = total_knockdowns > line
        
        result_payload = {
            'market_type': 'KD_OVER_UNDER',
            'line': line,
            'actual_total': total_knockdowns,
            'red_knockdowns': latest['red_knockdowns'],
            'blue_knockdowns': latest['blue_knockdowns'],
            'winning_side': 'OVER' if over_wins else 'UNDER'
        }
        
        return result_payload
    
    def settle_all_fight_markets(self, fight_id: UUID) -> List[Dict[str, Any]]:
        """
        Settle all open markets for a fight
        
        Calls settle_market() for each open market
        """
        # Get all open markets
        open_markets = self.get_fight_markets(fight_id, status=MarketStatus.OPEN)
        
        results = []
        for market in open_markets:
            result = self.settle_market(UUID(market['id']))
            results.append(result)
        
        return results
    
    def get_market_settlement(self, market_id: UUID) -> Optional[Dict]:
        """Get settlement for a market"""
        response = self.db.client.table('market_settlements')\
            .select('*')\
            .eq('market_id', str(market_id))\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_settled_markets(
        self,
        fight_id: Optional[UUID] = None,
        event_code: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all settled markets with settlements
        
        Args:
            fight_id: Optional filter by fight
            event_code: Optional filter by event
        
        Returns:
            List of markets with settlement data
        """
        # Build query
        query = """
            SELECT 
                m.*,
                ms.result_payload,
                ms.settled_at,
                f.code as fight_code
            FROM markets m
            LEFT JOIN market_settlements ms ON m.id = ms.market_id
            JOIN fights f ON m.fight_id = f.id
            WHERE m.status = 'SETTLED'
        """
        
        params = {}
        
        if fight_id:
            query += " AND m.fight_id = :fight_id"
            params['fight_id'] = str(fight_id)
        
        if event_code:
            query += """ 
                AND f.event_id = (
                    SELECT id FROM events WHERE code = :event_code
                )
            """
            params['event_code'] = event_code
        
        query += " ORDER BY ms.settled_at DESC"
        
        # Execute raw SQL
        # Note: Supabase client doesn't support raw SQL well, so we query both tables
        markets_response = self.db.client.table('markets')\
            .select('*, market_settlements(*), fights(code)')\
            .eq('status', 'SETTLED')
        
        if fight_id:
            markets_response = markets_response.eq('fight_id', str(fight_id))
        
        response = markets_response.execute()
        
        return response.data if response.data else []


# ========================================
# HELPER FUNCTIONS
# ========================================

def validate_market_params(market_type: MarketType, params: Dict[str, Any]) -> bool:
    """
    Validate market parameters based on type
    
    Returns True if valid, raises ValueError if invalid
    """
    if market_type == MarketType.WINNER:
        # Winner markets should have odds
        if 'red_odds' not in params or 'blue_odds' not in params:
            raise ValueError("WINNER market requires red_odds and blue_odds")
    
    elif market_type in [MarketType.TOTAL_SIG_STRIKES, MarketType.KD_OVER_UNDER, MarketType.SUB_ATT_OVER_UNDER]:
        # Over/under markets must have a line
        if 'line' not in params:
            raise ValueError(f"{market_type.value} market requires a line parameter")
        
        # Validate line is numeric
        try:
            float(params['line'])
        except (ValueError, TypeError):
            raise ValueError(f"Line must be numeric, got {params['line']}")
    
    return True


def create_standard_markets_for_fight(
    db_client,
    fight_id: UUID,
    config: Optional[Dict[str, Any]] = None
) -> List[Dict]:
    """
    Create a standard set of markets for a fight
    
    Args:
        db_client: Database client
        fight_id: Fight UUID
        config: Optional configuration for lines and odds
    
    Returns:
        List of created markets
    """
    settler = MarketSettler(db_client)
    
    # Default config
    if not config:
        config = {
            'winner': {'red_odds': 1.91, 'blue_odds': 1.91},
            'total_sig_strikes': {'line': 50.5, 'over_odds': 1.91, 'under_odds': 1.91},
            'kd_over_under': {'line': 0.5, 'over_odds': 2.50, 'under_odds': 1.50},
            'sub_att_over_under': {'line': 1.5, 'over_odds': 2.00, 'under_odds': 1.80}
        }
    
    markets = []
    
    # WINNER market
    try:
        market = settler.create_market(
            fight_id,
            MarketType.WINNER,
            config['winner']
        )
        markets.append(market)
    except Exception as e:
        logger.error(f"Failed to create WINNER market: {e}")
    
    # TOTAL_SIG_STRIKES market
    try:
        market = settler.create_market(
            fight_id,
            MarketType.TOTAL_SIG_STRIKES,
            config['total_sig_strikes']
        )
        markets.append(market)
    except Exception as e:
        logger.error(f"Failed to create TOTAL_SIG_STRIKES market: {e}")
    
    # KD_OVER_UNDER market
    try:
        market = settler.create_market(
            fight_id,
            MarketType.KD_OVER_UNDER,
            config['kd_over_under']
        )
        markets.append(market)
    except Exception as e:
        logger.error(f"Failed to create KD_OVER_UNDER market: {e}")
    
    logger.info(f"Created {len(markets)} markets for fight {fight_id}")
    
    return markets
