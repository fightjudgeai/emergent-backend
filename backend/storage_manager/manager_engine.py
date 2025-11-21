"""
Storage Manager - Manager Engine
"""

import logging
from typing import List
from .models import StorageStats, CleanupResult, ArchiveResult

logger = logging.getLogger(__name__)


class StorageManagerEngine:
    """Manage storage for fight recordings"""
    
    def __init__(self, storage_path: str = "/var/fight-storage"):
        self.storage_path = storage_path
        
        # Mock storage data
        self.total_space_gb = 1000.0
        self.used_space_gb = 750.0
    
    def get_status(self) -> StorageStats:
        """
        Get current storage status
        
        Returns:
            StorageStats
        """
        free_space = self.total_space_gb - self.used_space_gb
        used_pct = (self.used_space_gb / self.total_space_gb) * 100
        
        # Determine alert level
        if used_pct >= 90:
            alert_level = "critical"
        elif used_pct >= 80:
            alert_level = "warning"
        else:
            alert_level = "normal"
        
        stats = StorageStats(
            total_space_gb=self.total_space_gb,
            used_space_gb=self.used_space_gb,
            free_space_gb=free_space,
            used_percentage=used_pct,
            alert_level=alert_level,
            recordings_gb=500.0,
            highlights_gb=150.0,
            replays_gb=50.0,
            archives_gb=50.0
        )
        
        logger.info(f"Storage status: {used_pct:.1f}% used ({alert_level})")
        return stats
    
    async def cleanup_expired(self, days: int = 7) -> CleanupResult:
        """
        Delete expired clips and recordings
        
        Args:
            days: Delete files older than this many days
        
        Returns:
            CleanupResult
        """
        # Mock cleanup
        files_deleted = 42
        space_freed = 50.0  # GB
        
        self.used_space_gb -= space_freed
        
        result = CleanupResult(
            files_deleted=files_deleted,
            space_freed_gb=space_freed
        )
        
        logger.info(f"Cleanup complete: {files_deleted} files, {space_freed}GB freed")
        return result
    
    async def archive_bout(self, bout_id: str) -> ArchiveResult:
        """
        Archive full fight bundle
        
        Args:
            bout_id: Bout to archive
        
        Returns:
            ArchiveResult
        """
        # Mock archival
        archive_url = f"s3://fight-archives/{bout_id}/full_bundle.tar.gz"
        archive_size = 25.0  # GB
        
        result = ArchiveResult(
            bout_id=bout_id,
            archive_url=archive_url,
            archive_size_gb=archive_size
        )
        
        logger.info(f"Bout {bout_id} archived: {archive_size}GB")
        return result
