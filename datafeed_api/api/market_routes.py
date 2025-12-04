"""
Sportsbook Market API Routes
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Query

from models.market_models import (
    MarketType,
    MarketStatus,
    CreateMarketRequest,
    CreateStandardMarketsRequest,
    UpdateMarketStatusRequest,
    SettleMarketRequest,
    SettleFightMarketsRequest,
    MarketResponse,
    SettleMarketResponse,
    BulkSettlementResponse,
    MarketStatistics
)
from services.market_settler import MarketSettler, create_standard_markets_for_fight

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["Sportsbook Markets"])

# Global service instance
market_settler: Optional[MarketSettler] = None


def set_market_settler(settler: MarketSettler):
    """Set the market settler service"""
    global market_settler
    market_settler = settler


# ========================================
# MARKET MANAGEMENT
# ========================================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_market(request: CreateMarketRequest):
    """
    Create a new sportsbook market
    
    Creates a market for betting on a specific fight outcome or statistic.
    
    **Market Types:**
    - WINNER: Bet on fight winner
    - TOTAL_SIG_STRIKES: Over/under on total significant strikes
    - KD_OVER_UNDER: Over/under on knockdowns
    - SUB_ATT_OVER_UNDER: Over/under on submission attempts
    
    **Example params:**
    - WINNER: `{"red_odds": 1.75, "blue_odds": 2.10}`
    - TOTAL_SIG_STRIKES: `{"line": 50.5, "over_odds": 1.91, "under_odds": 1.91}`
    """
    try:
        market = market_settler.create_market(
            request.fight_id,
            request.market_type,
            request.params,
            request.status
        )
        return market
    except Exception as e:
        logger.error(f"Error creating market: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create market: {str(e)}"
        )


@router.post("/standard")
async def create_standard_markets(request: CreateStandardMarketsRequest):
    """
    Create standard market set for a fight
    
    Creates a predefined set of markets:
    - WINNER
    - TOTAL_SIG_STRIKES (line: 50.5)
    - KD_OVER_UNDER (line: 0.5)
    
    **config** (optional): Custom lines and odds
    ```json
    {
      "winner": {"red_odds": 1.75, "blue_odds": 2.10},
      "total_sig_strikes": {"line": 60.5, "over_odds": 1.85, "under_odds": 1.95},
      "kd_over_under": {"line": 0.5, "over_odds": 2.50, "under_odds": 1.50}
    }
    ```
    """
    try:
        markets = create_standard_markets_for_fight(
            market_settler.db,
            request.fight_id,
            request.config
        )
        return {
            "success": True,
            "fight_id": str(request.fight_id),
            "markets_created": len(markets),
            "markets": markets
        }
    except Exception as e:
        logger.error(f"Error creating standard markets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create standard markets: {str(e)}"
        )


@router.get("/{market_id}")
async def get_market(market_id: UUID):
    """Get market by ID"""
    try:
        market = market_settler.get_market(market_id)
        
        if not market:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Market {market_id} not found"
            )
        
        # Get settlement if exists
        if market['status'] == 'SETTLED':
            settlement = market_settler.get_market_settlement(market_id)
            market['settlement'] = settlement
        
        return market
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market"
        )


@router.get("/fight/{fight_id}")
async def get_fight_markets(
    fight_id: UUID,
    status: Optional[MarketStatus] = Query(None, description="Filter by status")
):
    """
    Get all markets for a fight
    
    Optionally filter by status (OPEN, SUSPENDED, SETTLED, CANCELLED)
    """
    try:
        markets = market_settler.get_fight_markets(fight_id, status)
        
        return {
            "fight_id": str(fight_id),
            "status_filter": status.value if status else None,
            "total_markets": len(markets),
            "markets": markets
        }
    except Exception as e:
        logger.error(f"Error getting fight markets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fight markets"
        )


@router.patch("/{market_id}/status")
async def update_market_status(
    market_id: UUID,
    request: UpdateMarketStatusRequest
):
    """
    Update market status
    
    Change market status to:
    - OPEN: Accept bets
    - SUSPENDED: Temporarily closed
    - CANCELLED: Void all bets
    
    Note: SETTLED status is set automatically by settlement process
    """
    try:
        market = market_settler.update_market_status(market_id, request.status)
        
        if not market:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Market {market_id} not found"
            )
        
        return market
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating market status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update market status"
        )


# ========================================
# MARKET SETTLEMENT
# ========================================

@router.post("/settle/{market_id}", response_model=SettleMarketResponse)
async def settle_market(market_id: UUID):
    """
    Manually settle a market
    
    Settles market based on:
    - WINNER: Uses fight_results.winner_side
    - TOTAL_SIG_STRIKES: Uses round_state (red_sig_strikes + blue_sig_strikes)
    - KD_OVER_UNDER: Uses round_state (red_knockdowns + blue_knockdowns)
    - SUB_ATT_OVER_UNDER: Uses submission attempts (when tracked)
    
    Updates market status to SETTLED and creates settlement record.
    """
    try:
        result = market_settler.settle_market(market_id)
        return result
    except Exception as e:
        logger.error(f"Error settling market: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to settle market: {str(e)}"
        )


@router.post("/settle/fight/{fight_id}", response_model=BulkSettlementResponse)
async def settle_fight_markets(fight_id: UUID):
    """
    Settle all open markets for a fight
    
    Batch settlement for all markets associated with a fight.
    Useful for manual settlement or resettlement.
    
    **Note:** Markets are auto-settled when fight_results are added/updated.
    """
    try:
        results = market_settler.settle_all_fight_markets(fight_id)
        
        settled = sum(1 for r in results if r['success'])
        failed = len(results) - settled
        
        return {
            "fight_id": fight_id,
            "total_markets": len(results),
            "settled": settled,
            "failed": failed,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error settling fight markets: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to settle fight markets: {str(e)}"
        )


@router.get("/settlements/{market_id}")
async def get_market_settlement(market_id: UUID):
    """Get settlement details for a market"""
    try:
        settlement = market_settler.get_market_settlement(market_id)
        
        if not settlement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No settlement found for market {market_id}"
            )
        
        return settlement
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting settlement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settlement"
        )


@router.get("/settlements/fight/{fight_id}")
async def get_fight_settlements(fight_id: UUID):
    """Get all settlements for a fight"""
    try:
        settlements = market_settler.get_settled_markets(fight_id=fight_id)
        
        return {
            "fight_id": str(fight_id),
            "total_settlements": len(settlements),
            "settlements": settlements
        }
    except Exception as e:
        logger.error(f"Error getting fight settlements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settlements"
        )


# ========================================
# STATISTICS
# ========================================

@router.get("/stats/overview", response_model=MarketStatistics)
async def get_market_statistics():
    """Get overall market statistics"""
    try:
        # Get all markets
        all_markets_response = market_settler.db.client.table('markets')\
            .select('market_type, status')\
            .execute()
        
        all_markets = all_markets_response.data if all_markets_response.data else []
        
        # Calculate statistics
        total = len(all_markets)
        open_count = sum(1 for m in all_markets if m['status'] == 'OPEN')
        settled_count = sum(1 for m in all_markets if m['status'] == 'SETTLED')
        suspended_count = sum(1 for m in all_markets if m['status'] == 'SUSPENDED')
        cancelled_count = sum(1 for m in all_markets if m['status'] == 'CANCELLED')
        
        # Count by type
        by_type = {}
        for market in all_markets:
            market_type = market['market_type']
            by_type[market_type] = by_type.get(market_type, 0) + 1
        
        return {
            "total_markets": total,
            "open_markets": open_count,
            "settled_markets": settled_count,
            "suspended_markets": suspended_count,
            "cancelled_markets": cancelled_count,
            "by_type": by_type
        }
    except Exception as e:
        logger.error(f"Error getting market statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )
