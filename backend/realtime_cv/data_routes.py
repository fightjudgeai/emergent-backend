"""
Data Collection API Routes

Endpoints for managing training datasets:
- List available datasets
- Download datasets from GitHub/Kaggle
- Process datasets
- Upload local datasets
- Get collection statistics
"""

from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging

from .data_collection import DataCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cv-data", tags=["CV Data Collection"])

# Global data collector instance
data_collector: Optional[DataCollector] = None


def init_data_collector(db):
    """Initialize data collector"""
    global data_collector
    data_collector = DataCollector(db=db)
    logger.info("✅ CV Data Collector initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "CV Data Collection",
        "version": "1.0.0",
        "status": "operational"
    }


@router.get("/datasets")
async def list_datasets():
    """
    List all available training datasets
    
    Returns:
    - datasets: List of available datasets
    - count: Number of datasets
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        datasets = await data_collector.list_available_datasets()
        
        return {
            "datasets": datasets,
            "count": len(datasets)
        }
    
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{source_id}")
async def get_dataset_info(source_id: str):
    """
    Get detailed information about a specific dataset
    
    Path:
    - source_id: Dataset identifier
    
    Returns:
    - Dataset details including status, size, categories
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        info = await data_collector.get_dataset_info(source_id)
        
        if not info:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        return info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{source_id}/download")
async def download_dataset(source_id: str):
    """
    Download a dataset from its source
    
    Path:
    - source_id: Dataset identifier
    
    Returns:
    - success: Boolean indicating download success
    - message: Status message
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        success = await data_collector.download_dataset(source_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Dataset not found or download failed")
        
        return {
            "source_id": source_id,
            "success": True,
            "message": "Dataset downloaded successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{source_id}/process")
async def process_dataset(source_id: str):
    """
    Process a downloaded dataset
    
    Path:
    - source_id: Dataset identifier
    
    Returns:
    - success: Boolean indicating processing success
    - stats: Processing statistics (samples, categories, etc.)
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        result = await data_collector.process_dataset(source_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Processing failed"))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/upload")
async def upload_local_dataset(
    name: str = Form(...),
    description: str = Form(...),
    file_path: str = Form(...),
    categories: str = Form(...)  # Comma-separated
):
    """
    Register a locally uploaded dataset
    
    Form Data:
    - name: Dataset name
    - description: Dataset description
    - file_path: Path to uploaded files
    - categories: Comma-separated list of categories
    
    Returns:
    - Dataset information
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        # Parse categories
        category_list = [c.strip() for c in categories.split(",") if c.strip()]
        
        # Upload dataset
        dataset = await data_collector.upload_local_dataset(
            name=name,
            description=description,
            file_path=file_path,
            categories=category_list
        )
        
        return {
            "source_id": dataset.source_id,
            "name": dataset.name,
            "description": dataset.description,
            "categories": dataset.categories,
            "is_downloaded": dataset.is_downloaded,
            "message": "Local dataset registered successfully"
        }
    
    except Exception as e:
        logger.error(f"Error uploading dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_collection_stats():
    """
    Get overall data collection statistics
    
    Returns:
    - total_datasets: Total number of datasets
    - downloaded: Number of downloaded datasets
    - processed: Number of processed datasets
    - total_files: Total number of files
    - total_size_mb: Total size in megabytes
    - categories: All available categories
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        stats = await data_collector.get_collection_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-collect")
async def auto_collect_all():
    """
    Automatically download and process all available datasets
    
    This endpoint will:
    1. Download all datasets that haven't been downloaded
    2. Process all downloaded datasets
    3. Return detailed results
    
    Returns:
    - started_at: Start timestamp
    - completed_at: Completion timestamp
    - datasets: List of dataset results
    - success_count: Number of successful collections
    - failed_count: Number of failed collections
    """
    
    if not data_collector:
        raise HTTPException(status_code=500, detail="Data collector not initialized")
    
    try:
        results = await data_collector.auto_collect_all()
        return results
    
    except Exception as e:
        logger.error(f"Error in auto-collect: {e}")
        raise HTTPException(status_code=500, detail=str(e))
