"""
Fantasy Points Aggregator
Auto-computes fantasy points from fight stats with breakdown generation
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FightStats:
    """Fight statistics for a fighter"""
    sig_strikes_landed: int = 0
    knockdowns: int = 0
    takedowns_landed: int = 0
    control_seconds: int = 0
    submission_attempts: int = 0
    
    # Additional stats from round_state
    total_strikes: int = 0
    is_winner: bool = False
    finish_method: Optional[str] = None
    
    # AI metrics (for advanced profiles)
    ai_damage: float = 0.0
    ai_win_prob: float = 0.5
    
    # Accuracy metrics (for sportsbook)
    strikes_attempted: int = 0
    strikes_absorbed: int = 0


class FantasyAggregator:
    """
    Aggregates fight stats and computes fantasy points
    with automatic recomputation triggers
    """
    
    @staticmethod
    def compute_fantasy_points(
        fight_stats: FightStats,
        scoring_profile: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Compute fantasy points from fight stats using scoring profile
        
        Args:
            fight_stats: Fighter's aggregated stats
            scoring_profile: Scoring profile configuration (from fantasy_scoring_profiles.config)
        
        Returns:
            (total_points, breakdown) tuple where breakdown is JSON-serializable dict
        """
        cfg = scoring_profile.get('weights', {})
        bonuses = scoring_profile.get('bonuses', {})
        penalties = scoring_profile.get('penalties', {})
        thresholds = scoring_profile.get('thresholds', {})
        
        # Initialize breakdown
        breakdown = {
            'base_points': {},
            'bonuses': {},
            'penalties': {},
            'multipliers': {},
            'raw_stats': {}
        }
        
        total_points = 0.0
        
        # ========================================
        # BASE POINTS CALCULATION
        # ========================================
        
        # Significant strikes
        sig_strikes_points = fight_stats.sig_strikes_landed * cfg.get('sig_strike', 0)
        breakdown['base_points']['sig_strikes'] = round(sig_strikes_points, 2)
        total_points += sig_strikes_points
        
        # Knockdowns
        knockdown_points = fight_stats.knockdowns * cfg.get('knockdown', 0)
        breakdown['base_points']['knockdowns'] = round(knockdown_points, 2)
        total_points += knockdown_points
        
        # Takedowns
        takedown_points = fight_stats.takedowns_landed * cfg.get('takedown', 0)
        breakdown['base_points']['takedowns'] = round(takedown_points, 2)
        total_points += takedown_points
        
        # Control time (convert seconds to minutes)
        control_points = (fight_stats.control_seconds / 60.0) * cfg.get('control_minute', 0)
        breakdown['base_points']['control'] = round(control_points, 2)
        total_points += control_points
        
        # Submission attempts
        submission_points = fight_stats.submission_attempts * cfg.get('submission_attempt', 0)
        breakdown['base_points']['submission_attempts'] = round(submission_points, 2)
        total_points += submission_points
        
        # ========================================
        # ADVANCED MULTIPLIERS (fantasy.advanced, sportsbook.pro)
        # ========================================
        
        # AI damage multiplier
        if 'ai_damage_multiplier' in cfg and fight_stats.ai_damage > 0:
            ai_damage_bonus = fight_stats.ai_damage * cfg['ai_damage_multiplier']
            breakdown['multipliers']['ai_damage'] = round(ai_damage_bonus, 2)
            total_points += ai_damage_bonus
        
        # AI control multiplier
        if 'ai_control_multiplier' in cfg and fight_stats.ai_win_prob > 0.5:
            ai_control_bonus = (fight_stats.ai_win_prob - 0.5) * 100 * cfg['ai_control_multiplier']
            breakdown['multipliers']['ai_control'] = round(ai_control_bonus, 2)
            total_points += ai_control_bonus
        
        # Strike accuracy multiplier (sportsbook.pro)
        if 'strike_accuracy_multiplier' in cfg and fight_stats.strikes_attempted > 0:
            accuracy = fight_stats.sig_strikes_landed / fight_stats.strikes_attempted
            accuracy_bonus = accuracy * 100 * cfg['strike_accuracy_multiplier']
            breakdown['multipliers']['strike_accuracy'] = round(accuracy_bonus, 2)
            total_points += accuracy_bonus
        
        # Defense multiplier (sportsbook.pro)
        if 'defense_multiplier' in cfg and fight_stats.strikes_absorbed > 0:
            # Lower is better for defense
            defense_score = max(0, 100 - fight_stats.strikes_absorbed)
            defense_bonus = defense_score * cfg['defense_multiplier']
            breakdown['multipliers']['defense'] = round(defense_bonus, 2)
            total_points += defense_bonus
        
        # ========================================
        # BONUSES
        # ========================================
        
        # Win bonus
        if fight_stats.is_winner and 'win_bonus' in bonuses:
            breakdown['bonuses']['win'] = bonuses['win_bonus']
            total_points += bonuses['win_bonus']
        
        # Finish bonus (KO/TKO/SUB)
        if fight_stats.finish_method in ['KO', 'TKO', 'SUB', 'Submission']:
            if 'finish_bonus' in bonuses:
                breakdown['bonuses']['finish'] = bonuses['finish_bonus']
                total_points += bonuses['finish_bonus']
            
            # Specific finish bonuses
            if fight_stats.finish_method in ['KO', 'TKO'] and 'ko_bonus' in bonuses:
                breakdown['bonuses']['ko'] = bonuses['ko_bonus']
                total_points += bonuses['ko_bonus']
            
            if fight_stats.finish_method in ['SUB', 'Submission'] and 'submission_bonus' in bonuses:
                breakdown['bonuses']['submission'] = bonuses['submission_bonus']
                total_points += bonuses['submission_bonus']
        
        # Dominant round bonus
        if 'dominant_round_bonus' in bonuses:
            dominant_rounds = 0
            
            # Check damage threshold
            if thresholds.get('dominant_damage_threshold'):
                if fight_stats.ai_damage >= thresholds['dominant_damage_threshold']:
                    dominant_rounds += 1
            
            # Check control threshold
            if thresholds.get('dominant_control_threshold'):
                if fight_stats.control_seconds >= thresholds['dominant_control_threshold']:
                    dominant_rounds += 1
            
            if dominant_rounds > 0:
                dominant_bonus = dominant_rounds * bonuses['dominant_round_bonus']
                breakdown['bonuses']['dominant_rounds'] = round(dominant_bonus, 2)
                breakdown['bonuses']['dominant_rounds_count'] = dominant_rounds
                total_points += dominant_bonus
        
        # Clean sweep bonus (sportsbook.pro)
        # TODO: Implement clean sweep detection (requires round-by-round scoring)
        
        # ========================================
        # PENALTIES (sportsbook.pro)
        # ========================================
        
        # TODO: Implement penalty tracking (requires additional data)
        # - Point deductions
        # - Fouls
        
        # ========================================
        # RAW STATS FOR REFERENCE
        # ========================================
        
        breakdown['raw_stats'] = {
            'sig_strikes_landed': fight_stats.sig_strikes_landed,
            'knockdowns': fight_stats.knockdowns,
            'takedowns_landed': fight_stats.takedowns_landed,
            'control_seconds': fight_stats.control_seconds,
            'submission_attempts': fight_stats.submission_attempts,
            'total_strikes': fight_stats.total_strikes,
            'is_winner': fight_stats.is_winner,
            'finish_method': fight_stats.finish_method,
            'ai_damage': round(fight_stats.ai_damage, 2),
            'ai_win_prob': round(fight_stats.ai_win_prob, 3)
        }
        
        if fight_stats.strikes_attempted > 0:
            breakdown['raw_stats']['strike_accuracy'] = round(
                (fight_stats.sig_strikes_landed / fight_stats.strikes_attempted) * 100,
                1
            )
        
        # ========================================
        # SUMMARY
        # ========================================
        
        breakdown['summary'] = {
            'total_base_points': round(sum(breakdown['base_points'].values()), 2),
            'total_bonuses': round(sum(breakdown['bonuses'].values()), 2),
            'total_multipliers': round(sum(breakdown['multipliers'].values()), 2),
            'total_penalties': round(sum(breakdown['penalties'].values()), 2),
            'grand_total': round(total_points, 2)
        }
        
        return round(total_points, 2), breakdown
    
    @staticmethod
    def aggregate_fight_stats_from_rounds(round_states: list[Dict], corner: str) -> FightStats:
        """
        Aggregate fight stats from multiple round_state records
        
        Args:
            round_states: List of round_state records (from database)
            corner: 'RED' or 'BLUE'
        
        Returns:
            FightStats object with aggregated data
        """
        stats = FightStats()
        
        if not round_states:
            return stats
        
        # Aggregate from latest round (cumulative stats)
        latest_round = max(round_states, key=lambda r: r['seq'])
        
        if corner == 'RED':
            stats.sig_strikes_landed = latest_round.get('red_sig_strikes', 0)
            stats.total_strikes = latest_round.get('red_strikes', 0)
            stats.knockdowns = latest_round.get('red_knockdowns', 0)
            stats.control_seconds = latest_round.get('red_control_sec', 0)
            stats.ai_damage = float(latest_round.get('red_ai_damage', 0))
            stats.ai_win_prob = float(latest_round.get('red_ai_win_prob', 0.5))
        else:  # BLUE
            stats.sig_strikes_landed = latest_round.get('blue_sig_strikes', 0)
            stats.total_strikes = latest_round.get('blue_strikes', 0)
            stats.knockdowns = latest_round.get('blue_knockdowns', 0)
            stats.control_seconds = latest_round.get('blue_control_sec', 0)
            stats.ai_damage = float(latest_round.get('blue_ai_damage', 0))
            stats.ai_win_prob = float(latest_round.get('blue_ai_win_prob', 0.5))
        
        # Calculate strike accuracy
        if stats.total_strikes > 0:
            stats.strikes_attempted = stats.total_strikes
        
        # Note: takedowns and submission_attempts would need to be added to round_state schema
        # For now, they default to 0
        
        return stats
    
    @staticmethod
    def add_fight_result_to_stats(stats: FightStats, fight_result: Optional[Dict], corner: str) -> FightStats:
        """
        Add fight result information to stats
        
        Args:
            stats: FightStats object
            fight_result: fight_results record (from database)
            corner: 'RED' or 'BLUE'
        
        Returns:
            Updated FightStats object
        """
        if fight_result:
            stats.is_winner = (fight_result['winner_side'] == corner)
            stats.finish_method = fight_result.get('method')
        
        return stats


def compute_and_save_fantasy_stats(
    db_client,
    fight_id: str,
    fighter_id: str,
    corner: str,
    profile_id: str
) -> Dict[str, Any]:
    """
    Auto-compute fantasy stats from fight data and save to database
    
    This is called by triggers when:
    - round_state changes
    - round locks
    - fight_results updated
    
    Args:
        db_client: Database client
        fight_id: Fight UUID
        fighter_id: Fighter UUID
        corner: 'RED' or 'BLUE'
        profile_id: Scoring profile ID
    
    Returns:
        Result dict with success status and data
    """
    try:
        # Get scoring profile
        profile_response = db_client.table('fantasy_scoring_profiles')\
            .select('*')\
            .eq('id', profile_id)\
            .execute()
        
        if not profile_response.data:
            raise Exception(f"Profile {profile_id} not found")
        
        profile = profile_response.data[0]
        
        # Get all round states for this fight
        rounds_response = db_client.table('round_state')\
            .select('*')\
            .eq('fight_id', fight_id)\
            .order('seq')\
            .execute()
        
        round_states = rounds_response.data if rounds_response.data else []
        
        # Get fight result
        result_response = db_client.table('fight_results')\
            .select('*')\
            .eq('fight_id', fight_id)\
            .execute()
        
        fight_result = result_response.data[0] if result_response.data else None
        
        # Aggregate stats
        aggregator = FantasyAggregator()
        fight_stats = aggregator.aggregate_fight_stats_from_rounds(round_states, corner)
        fight_stats = aggregator.add_fight_result_to_stats(fight_stats, fight_result, corner)
        
        # Compute fantasy points
        total_points, breakdown = aggregator.compute_fantasy_points(
            fight_stats,
            profile['config']
        )
        
        # Save to database (upsert)
        save_response = db_client.table('fantasy_fight_stats')\
            .upsert({
                'fight_id': fight_id,
                'fighter_id': fighter_id,
                'profile_id': profile_id,
                'fantasy_points': total_points,
                'breakdown': breakdown
            }, on_conflict='fight_id,fighter_id,profile_id')\
            .execute()
        
        logger.info(f"Computed fantasy stats: fight={fight_id}, fighter={fighter_id}, profile={profile_id}, points={total_points}")
        
        return {
            'success': True,
            'fight_id': fight_id,
            'fighter_id': fighter_id,
            'profile_id': profile_id,
            'fantasy_points': total_points,
            'breakdown': breakdown
        }
    
    except Exception as e:
        logger.error(f"Error computing fantasy stats: {e}")
        return {
            'success': False,
            'error': str(e)
        }
