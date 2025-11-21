"""
Scoring Simulator - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .simulator_engine import ScoringSimulatorEngine
from .models import SimulationScript, SimulationResult

logger = logging.getLogger(__name__)

scoring_simulator_api = APIRouter(tags=["Scoring Simulator"])
simulator_engine: Optional[ScoringSimulatorEngine] = None

def get_simulator_engine():
    if simulator_engine is None:
        raise HTTPException(status_code=500, detail="Scoring Simulator not initialized")
    return simulator_engine

@scoring_simulator_api.post("/simulate", response_model=SimulationResult)
async def run_simulation(script: SimulationScript):
    """Run scoring simulation"""
    engine = get_simulator_engine()
    return await engine.run_simulation(script)

@scoring_simulator_api.get("/results/{bout_id}", response_model=SimulationResult)
async def get_simulation_results(bout_id: str):
    """Get simulation results"""
    engine = get_simulator_engine()
    if bout_id not in engine.simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return engine.simulations[bout_id]

@scoring_simulator_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Scoring Simulator", "version": "1.0.0"}
