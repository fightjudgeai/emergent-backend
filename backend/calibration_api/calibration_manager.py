"""
Calibration API - Calibration Manager
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from .models import CalibrationConfig, CalibrationHistory
import sys
sys.path.append('/app/backend')

logger = logging.getLogger(__name__)


class CalibrationManager:
    """Manage system calibration parameters"""
    
    def __init__(self, db=None, postgres_session=None, redis_pubsub=None):
        self.db = db  # MongoDB
        self.postgres_session = postgres_session  # Postgres session factory
        self.redis_pubsub = redis_pubsub  # Redis pub/sub for broadcasting
        
        # Default configuration
        self.config = CalibrationConfig()
        
        # History tracking
        self.history: List[CalibrationHistory] = []
        
        # Load from database if available
        if self.postgres_session is not None:
            # Load from Postgres (async initialization will be handled separately)
            logger.info("Postgres session available for calibration storage")
        elif self.db is not None:
            # Fallback to MongoDB
            logger.info("Using MongoDB for calibration storage")
    
    def get_config(self) -> CalibrationConfig:
        """
        Get current calibration configuration
        
        Returns:
            CalibrationConfig
        """
        return self.config
    
    async def set_config(
        self,
        config: CalibrationConfig,
        modified_by: str = "system"
    ) -> CalibrationConfig:
        """
        Update calibration configuration
        
        Args:
            config: New configuration
            modified_by: Who made the change
        
        Returns:
            Updated CalibrationConfig
        """
        # Track changes
        old_config = self.config
        
        # Record history for each changed parameter
        if config.kd_threshold != old_config.kd_threshold:
            self._record_change("kd_threshold", old_config.kd_threshold, config.kd_threshold, modified_by)
        
        if config.rocked_threshold != old_config.rocked_threshold:
            self._record_change("rocked_threshold", old_config.rocked_threshold, config.rocked_threshold, modified_by)
        
        if config.highimpact_strike_threshold != old_config.highimpact_strike_threshold:
            self._record_change("highimpact_strike_threshold", old_config.highimpact_strike_threshold, config.highimpact_strike_threshold, modified_by)
        
        if config.momentum_swing_window_ms != old_config.momentum_swing_window_ms:
            self._record_change("momentum_swing_window_ms", float(old_config.momentum_swing_window_ms), float(config.momentum_swing_window_ms), modified_by)
        
        if config.multicam_merge_window_ms != old_config.multicam_merge_window_ms:
            self._record_change("multicam_merge_window_ms", float(old_config.multicam_merge_window_ms), float(config.multicam_merge_window_ms), modified_by)
        
        # Update configuration
        config.last_modified = datetime.now(timezone.utc)
        config.modified_by = modified_by
        self.config = config
        
        # Save to Postgres
        await self._save_to_postgres(config)
        
        # Broadcast via Redis pub/sub
        await self._broadcast_config_change(config)
        
        # Replicate to CV Analytics Engine
        await self._replicate_to_cv_engine()
        
        logger.info(f"Calibration updated by {modified_by}")
        return self.config
    
    async def _save_to_postgres(self, config: CalibrationConfig):
        """Save configuration to Postgres"""
        if not self.postgres_session:
            logger.debug("Postgres not available, skipping save")
            return
        
        try:
            from db_utils import CalibrationConfigDB
            from sqlalchemy import select, update
            
            async with self.postgres_session() as session:
                # Deactivate all existing configs
                await session.execute(
                    update(CalibrationConfigDB).values(is_active=0)
                )
                
                # Insert new active config
                new_config = CalibrationConfigDB(
                    kd_threshold=config.kd_threshold,
                    rocked_threshold=config.rocked_threshold,
                    highimpact_strike_threshold=config.highimpact_strike_threshold,
                    momentum_swing_window_ms=config.momentum_swing_window_ms,
                    multicam_merge_window_ms=config.multicam_merge_window_ms,
                    confidence_threshold=config.confidence_threshold,
                    deduplication_window_ms=config.deduplication_window_ms,
                    version=config.version,
                    modified_by=config.modified_by,
                    is_active=1
                )
                
                session.add(new_config)
                await session.commit()
                logger.info("Configuration saved to Postgres")
        
        except Exception as e:
            logger.error(f"Error saving to Postgres: {e}")
    
    async def _broadcast_config_change(self, config: CalibrationConfig):
        """Broadcast config change via Redis pub/sub"""
        if not self.redis_pubsub:
            logger.debug("Redis pub/sub not available, skipping broadcast")
            return
        
        try:
            message = {
                "type": "config_update",
                "config": config.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.redis_pubsub.publish(message)
            logger.info("Configuration change broadcasted via Redis")
        
        except Exception as e:
            logger.error(f"Error broadcasting config change: {e}")
    
    async def reset_config(self) -> CalibrationConfig:
        """
        Reset to default configuration
        
        Returns:
            Default CalibrationConfig
        """
        self.config = CalibrationConfig()
        
        # Save to database
        if self.db:
            pass
        
        # Replicate
        await self._replicate_to_cv_engine()
        
        logger.info("Calibration reset to defaults")
        return self.config
    
    def _record_change(self, parameter: str, old_value: float, new_value: float, modified_by: str):
        """Record calibration change in history"""
        change = CalibrationHistory(
            timestamp=datetime.now(timezone.utc),
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            modified_by=modified_by
        )
        
        self.history.append(change)
        
        # Keep only recent history
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        logger.info(f"Calibration change: {parameter} {old_value} → {new_value}")
    
    async def _replicate_to_cv_engine(self):
        """
        Replicate configuration to CV Analytics Engine
        
        In production:
        - Push to CV Analytics Engine via API
        - Update event pipeline thresholds
        - Update multicam fusion timing
        """
        logger.info("Replicating calibration to CV Analytics Engine")
        # Mock replication
        pass
    
    def get_history(self, limit: int = 50) -> List[CalibrationHistory]:
        """Get calibration change history"""
        return self.history[-limit:]
