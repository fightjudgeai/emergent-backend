"""
Scoring Simulator - Simulation Engine
"""

import asyncio
import logging
from typing import Dict
import time
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent
from .models import SimulationScript, SimulationResult, RoundSimulationResult

logger = logging.getLogger(__name__)


class ScoringSimulatorEngine:
    """Replay fight events for validation"""
    
    def __init__(self):
        self.simulations: Dict[str, SimulationResult] = {}
    
    async def run_simulation(self, script: SimulationScript) -> SimulationResult:
        """
        Run simulation from script
        
        Args:
            script: Simulation script with events
        
        Returns:
            SimulationResult
        """
        logger.info(f"Starting simulation for {script.bout_id} at {script.speed_multiplier}x speed")
        
        start_time = time.time()
        
        # Group events by round
        events_by_round = self._group_by_round(script.events)
        
        # Process each round
        round_results = []
        for round_num, round_events in events_by_round.items():
            result = await self._simulate_round(round_num, round_events, script.speed_multiplier)
            round_results.append(result)
        
        # Calculate final result
        final_score = self._calculate_final_score(round_results)
        winner = self._determine_winner(round_results)
        
        # Event correlations
        correlations = self._analyze_correlations(script.events)
        
        duration = time.time() - start_time
        
        result = SimulationResult(
            bout_id=script.bout_id,
            round_results=round_results,
            final_score=final_score,
            winner=winner,
            total_events_processed=len(script.events),
            simulation_duration_sec=duration,
            event_correlations=correlations
        )
        
        self.simulations[script.bout_id] = result
        
        logger.info(f"Simulation complete: {final_score} ({duration:.2f}s)")
        return result
    
    def _group_by_round(self, events: list) -> Dict[int, list]:
        """Group events by round number"""
        rounds = {}
        for event in events:
            # Extract round number from round_id (e.g., "round_1" -> 1)
            try:
                round_num = int(event.round_id.split('_')[-1])
            except:
                round_num = 1
            
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(event)
        
        return rounds
    
    async def _simulate_round(
        self,
        round_num: int,
        events: list,
        speed: float
    ) -> RoundSimulationResult:
        """
        Simulate single round
        """
        # Mock scoring (in production: use actual scoring engine)
        judge_events = [e for e in events if e.source.value == "manual"]
        cv_events = [e for e in events if e.source.value == "cv_system"]
        
        # Simulate event processing with speed multiplier
        for event in events:
            await asyncio.sleep(0.01 / speed)  # Adjust delay by speed
        
        # Mock score calculation
        fighter_a_score = len([e for e in events if e.fighter_id == "fighter_a"]) * 2.5
        fighter_b_score = len([e for e in events if e.fighter_id == "fighter_b"]) * 2.5
        
        if abs(fighter_a_score - fighter_b_score) < 5:
            score_card = "10-10"
            winner = "draw"
        elif fighter_a_score > fighter_b_score:
            score_card = "10-9"
            winner = "fighter_a"
        else:
            score_card = "9-10"
            winner = "fighter_b"
        
        return RoundSimulationResult(
            round_num=round_num,
            score_card=score_card,
            winner=winner,
            confidence=0.85,
            fighter_a_total=fighter_a_score,
            fighter_b_total=fighter_b_score,
            total_events=len(events),
            judge_events=len(judge_events),
            cv_events=len(cv_events)
        )
    
    def _calculate_final_score(self, round_results: list) -> str:
        """Calculate final scorecard"""
        scores = [r.score_card for r in round_results]
        return ", ".join(scores)
    
    def _determine_winner(self, round_results: list) -> str:
        """Determine fight winner"""
        fighter_a_rounds = len([r for r in round_results if r.winner == "fighter_a"])
        fighter_b_rounds = len([r for r in round_results if r.winner == "fighter_b"])
        
        if fighter_a_rounds > fighter_b_rounds:
            return "fighter_a"
        elif fighter_b_rounds > fighter_a_rounds:
            return "fighter_b"
        else:
            return "draw"
    
    def _analyze_correlations(self, events: list) -> Dict[str, int]:
        """Analyze event correlations"""
        correlations = {}
        for event in events:
            key = f"{event.event_type.value}_{event.source.value}"
            correlations[key] = correlations.get(key, 0) + 1
        return correlations
