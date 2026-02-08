"""
Database Utilities for Postgres Support
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Postgres configuration from environment
POSTGRES_URL = os.getenv(
    'POSTGRES_URL',
    'postgresql+asyncpg://postgres:postgres@localhost:5432/fjaipos'
)

# Create async engine
engine = None
SessionLocal = None

try:
    engine = create_async_engine(
        POSTGRES_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    logger.info(f"Postgres engine created: {POSTGRES_URL.split('@')[1] if '@' in POSTGRES_URL else 'localhost'}")
except Exception as e:
    logger.warning(f"Postgres not available: {e}")
    engine = None
    SessionLocal = None


# Calibration Config Table
class CalibrationConfigDB(Base):
    __tablename__ = 'calibration_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    kd_threshold = Column(Float, nullable=False, default=0.75)
    rocked_threshold = Column(Float, nullable=False, default=0.65)
    highimpact_strike_threshold = Column(Float, nullable=False, default=0.70)
    momentum_swing_window_ms = Column(Integer, nullable=False, default=1200)
    multicam_merge_window_ms = Column(Integer, nullable=False, default=150)
    confidence_threshold = Column(Float, nullable=False, default=0.5)
    deduplication_window_ms = Column(Integer, nullable=False, default=100)
    version = Column(String(20), nullable=False, default='1.0.0')
    modified_by = Column(String(100), nullable=False, default='system')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Integer, nullable=False, default=1)  # 1=active, 0=inactive


# Round Validation Results Table
class RoundValidationResultDB(Base):
    __tablename__ = 'round_validation_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(String(100), nullable=False, unique=True, index=True)
    bout_id = Column(String(100), nullable=False, index=True)
    round_num = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # ok, warnings, failed
    issues = Column(JSON, nullable=True)
    event_count = Column(Integer, nullable=False, default=0)
    validated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


async def init_db():
    """Initialize database tables"""
    if engine is None:
        logger.warning("Postgres engine not available, skipping table creation")
        return
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")


async def get_db():
    """Get database session"""
    if SessionLocal is None:
        yield None
        return
    
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
