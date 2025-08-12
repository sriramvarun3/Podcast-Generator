"""
Job queue service for managing podcast generation jobs.
Handles job tracking, status updates, and background processing.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from loguru import logger

from app.models.podcast import JobStatus, ProgressUpdate, PodcastResult
from app.core.config import settings


class JobState(Enum):
    """Job states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job information."""
    job_id: str
    status: JobState
    topic: str
    description: str
    tone: str
    target_length: int
    progress: Optional[ProgressUpdate] = None
    result: Optional[PodcastResult] = None
    error: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_callback: Optional[Callable] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['progress_callback'] = None  # Don't serialize callback
        return data


class JobQueue:
    """Job queue for managing podcast generation jobs."""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        # Don't start cleanup task during initialization to avoid event loop issues
        # self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
            except RuntimeError:
                # No running event loop, skip for now
                pass
    
    async def ensure_cleanup_task_running(self):
        """Ensure cleanup task is running (call this when app starts)."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
    
    async def _cleanup_old_jobs(self):
        """Clean up old completed/failed jobs."""
        while True:
            try:
                await asyncio.sleep(settings.job_cleanup_interval)
                
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                jobs_to_remove = []
                
                for job_id, job in self.jobs.items():
                    if (job.status in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED] and
                        job.updated_at < cutoff_time):
                        jobs_to_remove.append(job_id)
                
                for job_id in jobs_to_remove:
                    await self.remove_job(job_id)
                
                if jobs_to_remove:
                    logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
                    
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    async def create_job(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """Create a new job."""
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            status=JobState.PENDING,
            topic=topic,
            description=description,
            tone=tone,
            target_length=target_length,
            progress_callback=progress_callback
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} for topic: {topic}")
        
        return job_id
    
    async def start_job(self, job_id: str, generator_func: Callable) -> bool:
        """Start a job."""
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        job = self.jobs[job_id]
        
        if job.status != JobState.PENDING:
            logger.warning(f"Job {job_id} is not pending (status: {job.status})")
            return False
        
        # Update job status
        job.status = JobState.RUNNING
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        # Create background task
        task = asyncio.create_task(self._run_job(job_id, generator_func))
        self.running_jobs[job_id] = task
        
        logger.info(f"Started job {job_id}")
        return True
    
    async def _run_job(self, job_id: str, generator_func: Callable):
        """Run a job in the background."""
        try:
            # Get the job
            job = self.jobs[job_id]
            
            # Update progress
            await self._update_job_progress(job_id, 0, "Starting podcast generation...")
            
            # Run the generator function
            result = await generator_func(job_id)
            
            logger.info(f"🎯 [DEBUG] Generator function returned result: {type(result)}")
            logger.info(f"🎯 [DEBUG] Result status: {getattr(result, 'status', 'NO STATUS ATTR')}")
            logger.info(f"🎯 [DEBUG] Result mp3_url: {getattr(result, 'mp3_url', 'NO MP3_URL ATTR')}")
            
            # Update job with result
            if hasattr(result, 'status') and result.status == "error":
                job.status = JobState.FAILED
                job.error = result.error or "Podcast generation failed"
                logger.error(f"Job {job_id} failed: {job.error}")
            else:
                job.status = JobState.COMPLETED
                logger.info(f"Job {job_id} completed successfully")
                
            job.result = result
            logger.info(f"🎯 [DEBUG] Stored result in job: {job.result is not None}")
            if job.result:
                logger.info(f"🎯 [DEBUG] Stored result type: {type(job.result)}")
                logger.info(f"🎯 [DEBUG] Stored result mp3_url: {getattr(job.result, 'mp3_url', 'NO MP3_URL')}")
                
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            
            # Update final progress
            await self._update_job_progress(job_id, 100, "Podcast generation completed!")
            
        except asyncio.CancelledError:
            # Job was cancelled
            job = self.jobs[job_id]
            job.status = JobState.CANCELLED
            job.updated_at = datetime.utcnow()
            logger.info(f"Job {job_id} was cancelled")
            
        except Exception as e:
            # Job failed
            job = self.jobs[job_id]
            job.status = JobState.FAILED
            job.error = str(e)
            job.updated_at = datetime.utcnow()
            logger.error(f"Job {job_id} failed: {e}")
            
        finally:
            # Clean up running job
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    async def _update_job_progress(
        self,
        job_id: str,
        percent: float,
        message: str,
        log_entries: Optional[List[str]] = None
    ):
        """Update job progress."""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        
        # Create progress update
        progress = ProgressUpdate(
            stage=int(percent / 20),  # 5 stages
            message=message,
            percent=percent,
            log=log_entries or [message]
        )
        
        job.progress = progress
        job.updated_at = datetime.utcnow()
        
        # Call progress callback if available
        if job.progress_callback:
            try:
                await job.progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed for job {job_id}: {e}")
        
        logger.debug(f"Job {job_id} progress: {percent:.1f}% - {message}")
    
    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status."""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        logger.info(f"🔍 [DEBUG] get_job_status for {job_id}: status={job.status.value}")
        logger.info(f"🔍 [DEBUG] Job has result: {job.result is not None}")
        if job.result:
            logger.info(f"🔍 [DEBUG] Job result type: {type(job.result)}")
            logger.info(f"🔍 [DEBUG] Job result mp3_url: {getattr(job.result, 'mp3_url', 'NO MP3_URL')}")
        
        return JobStatus(
            job_id=job.job_id,
            topic=job.topic,
            status=job.status.value,
            progress=job.progress,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at
        )
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status not in [JobState.PENDING, JobState.RUNNING]:
            return False
        
        # Cancel running task if exists
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            task.cancel()
            del self.running_jobs[job_id]
        
        # Update job status
        job.status = JobState.CANCELLED
        job.updated_at = datetime.utcnow()
        
        logger.info(f"Job {job_id} cancelled")
        return True
    
    async def remove_job(self, job_id: str) -> bool:
        """Remove a job from the queue."""
        if job_id in self.running_jobs:
            # Cancel if running
            await self.cancel_job(job_id)
        
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Removed job {job_id}")
            return True
        
        return False
    
    async def get_all_jobs(self, limit: int = 100) -> List[JobStatus]:
        """Get all jobs (limited for performance)."""
        jobs = list(self.jobs.values())
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return [await self.get_job_status(job.job_id) for job in jobs[:limit]]
    
    async def get_jobs_by_status(self, status: JobState, limit: int = 50) -> List[JobStatus]:
        """Get jobs by status."""
        filtered_jobs = [
            job for job in self.jobs.values()
            if job.status == status
        ]
        filtered_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return [await self.get_job_status(job.job_id) for job in filtered_jobs[:limit]]
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        total_jobs = len(self.jobs)
        running_jobs = len(self.running_jobs)
        
        status_counts = {}
        for job in self.jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_jobs": total_jobs,
            "running_jobs": running_jobs,
            "status_counts": status_counts,
            "queue_health": "healthy" if running_jobs < 10 else "busy"
        }
    
    async def cleanup_failed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up failed jobs older than specified age."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        jobs_to_remove = []
        
        for job_id, job in self.jobs.items():
            if (job.status == JobState.FAILED and
                job.updated_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            await self.remove_job(job_id)
        
        logger.info(f"Cleaned up {len(jobs_to_remove)} failed jobs")
        return len(jobs_to_remove)


# Global job queue instance
job_queue = JobQueue() 