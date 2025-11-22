"""
Data Collection Engine - Build Proprietary Dataset
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from .models import *

logger = logging.getLogger(__name__)

class DataCollectionEngine:
    """Engine for building combat sports datasets"""
    
    def __init__(self, db=None):
        self.db = db
        
        # Video registry
        self.videos: Dict[str, TrainingVideo] = {}
        
        # Annotations
        self.annotations: Dict[str, List[Annotation]] = {}
        
        # Datasets
        self.datasets: Dict[str, DatasetSplit] = {}
    
    async def upload_video(self, video: TrainingVideo) -> TrainingVideo:
        """Upload training video to dataset"""
        
        self.videos[video.id] = video
        
        if self.db:
            try:
                video_dict = video.model_dump()
                video_dict['uploaded_at'] = video_dict['uploaded_at'].isoformat()
                await self.db.training_videos.insert_one(video_dict)
                logger.info(f"Video uploaded: {video.title}")
            except Exception as e:
                logger.error(f"Error storing video: {e}")
        
        return video
    
    async def add_annotation(self, annotation: Annotation) -> Annotation:
        """Add manual annotation to video frame"""
        
        video_id = annotation.video_id
        
        if video_id not in self.annotations:
            self.annotations[video_id] = []
        
        self.annotations[video_id].append(annotation)
        
        # Update video annotation progress
        if video_id in self.videos:
            video = self.videos[video_id]
            total_frames = int(video.duration_sec * video.fps)
            annotated_frames = len(self.annotations[video_id])
            video.annotation_progress = (annotated_frames / total_frames) * 100
            
            if video.annotation_progress >= 80:  # 80% annotated
                video.is_annotated = True
        
        if self.db:
            try:
                ann_dict = annotation.model_dump()
                ann_dict['annotated_at'] = ann_dict['annotated_at'].isoformat()
                await self.db.annotations.insert_one(ann_dict)
            except Exception as e:
                logger.error(f"Error storing annotation: {e}")
        
        return annotation
    
    async def create_dataset_split(self, name: str, version: str = "1.0.0") -> DatasetSplit:
        """Create train/val/test split from annotated videos"""
        
        # Get all annotated videos
        annotated_videos = [
            v for v in self.videos.values() if v.is_annotated
        ]
        
        if not annotated_videos:
            raise ValueError("No annotated videos available")
        
        # Split: 70% train, 20% val, 10% test
        import random
        random.shuffle(annotated_videos)
        
        total = len(annotated_videos)
        train_end = int(total * 0.7)
        val_end = int(total * 0.9)
        
        train_videos = [v.id for v in annotated_videos[:train_end]]
        val_videos = [v.id for v in annotated_videos[train_end:val_end]]
        test_videos = [v.id for v in annotated_videos[val_end:]]
        
        # Count annotations
        total_annotations = sum(len(self.annotations.get(v_id, [])) for v_id in self.videos.keys())
        
        # Count by class
        class_dist = {}
        for anns in self.annotations.values():
            for ann in anns:
                label = ann.label
                class_dist[label] = class_dist.get(label, 0) + 1
        
        dataset = DatasetSplit(
            name=name,
            version=version,
            train_videos=train_videos,
            val_videos=val_videos,
            test_videos=test_videos,
            total_videos=total,
            total_annotations=total_annotations,
            class_distribution=class_dist
        )
        
        self.datasets[dataset.dataset_id] = dataset
        
        if self.db:
            try:
                dataset_dict = dataset.model_dump()
                dataset_dict['created_at'] = dataset_dict['created_at'].isoformat()
                await self.db.datasets.insert_one(dataset_dict)
                logger.info(f"Dataset created: {name} v{version}")
            except Exception as e:
                logger.error(f"Error storing dataset: {e}")
        
        return dataset
    
    async def start_training_job(self, job: ModelTrainingJob) -> ModelTrainingJob:
        """Start model training job"""
        
        job.status = "training"
        job.started_at = datetime.now(timezone.utc)
        
        logger.info(f"Training job started: {job.model_name}")
        
        # In production: Start actual training
        # - Load dataset from storage
        # - Initialize model architecture
        # - Run training loop
        # - Save checkpoints
        # - Monitor metrics
        
        if self.db:
            try:
                job_dict = job.model_dump()
                if job_dict.get('started_at'):
                    job_dict['started_at'] = job_dict['started_at'].isoformat()
                await self.db.training_jobs.insert_one(job_dict)
            except Exception as e:
                logger.error(f"Error storing job: {e}")
        
        return job
    
    def get_annotation_stats(self, video_id: str) -> dict:
        """Get annotation statistics for a video"""
        
        if video_id not in self.annotations:
            return {"video_id": video_id, "total": 0}
        
        anns = self.annotations[video_id]
        
        # Count by type
        type_counts = {}
        for ann in anns:
            ann_type = ann.annotation_type
            type_counts[ann_type] = type_counts.get(ann_type, 0) + 1
        
        # Count by label
        label_counts = {}
        for ann in anns:
            label = ann.label
            label_counts[label] = label_counts.get(label, 0) + 1
        
        return {
            "video_id": video_id,
            "total_annotations": len(anns),
            "by_type": type_counts,
            "by_label": label_counts
        }
