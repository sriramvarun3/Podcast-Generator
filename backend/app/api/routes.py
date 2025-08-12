"""
API routes for the podcast generator.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from loguru import logger
import json
import os
import traceback
import time
import uuid

from app.models.podcast import (
    GenerateRequest, PodcastResult, JobStatus, ProgressUpdate
)
from app.services.podcast_generator import PodcastGenerator
from app.services.job_queue import job_queue

router = APIRouter(prefix="/api/v1", tags=["podcast"])

# Initialize services
podcast_generator = PodcastGenerator()

# Mock data storage for testing
mock_jobs = {}

@router.post("/mock/generate")
async def mock_generate_podcast(request: GenerateRequest):
    """
    MOCK: Generate a new podcast from the given request.
    Returns mock data that matches the frontend expectations.
    """
    request_id = f"req_{int(time.time() * 1000)}"
    job_id = f"mock_job_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"🎭 [MOCK] [{request_id}] Received mock podcast generation request")
    logger.info(f"📝 [MOCK] [{request_id}] Request data: {request.model_dump()}")
    logger.info(f"🎯 [MOCK] [{request_id}] Topic: '{request.topic}'")
    
    # Store mock job
    mock_jobs[job_id] = {
        "id": job_id,
        "topic": request.topic,
        "status": "pending",
        "progress": 0,
        "created_at": time.time(),
        "completed_at": None,
        "audio_url": None,
        "transcript": None,
        "metrics": None,
        "error": None
    }
    
    # Return the expected format
    result = {"id": job_id}
    
    logger.info(f"✅ [MOCK] [{request_id}] Mock job created with ID: {job_id}")
    logger.info(f"📊 [MOCK] [{request_id}] Returning: {result}")
    
    return result


@router.get("/mock/result/{job_id}")
async def mock_get_result(job_id: str):
    """
    MOCK: Get the result of a specific job.
    Returns mock data that progresses over time.
    """
    logger.info(f"🎭 [MOCK] Getting mock result for job ID: {job_id}")
    
    if job_id not in mock_jobs:
        logger.warning(f"⚠️ [MOCK] Mock job not found: {job_id}")
        # Create a mock job if it doesn't exist
        mock_jobs[job_id] = {
            "id": job_id,
            "topic": "Mock Topic",
            "status": "pending",
            "progress": 0,
            "created_at": time.time(),
            "completed_at": None,
            "audio_url": None,
            "transcript": None,
            "metrics": None,
            "error": None
        }
    
    job = mock_jobs[job_id]
    current_time = time.time()
    elapsed = current_time - job["created_at"]
    
    # Simulate progression over time
    if elapsed < 5:
        job["status"] = "pending"
        job["progress"] = min(10, int(elapsed * 2))
    elif elapsed < 15:
        job["status"] = "processing"
        job["progress"] = min(90, int(10 + (elapsed - 5) * 8))
    else:
        job["status"] = "completed"
        job["progress"] = 100
        job["completed_at"] = current_time
        job["audio_url"] = "http://localhost:8000/api/v1/mock/audio/sample.mp3"
        job["transcript"] = f"This is a mock podcast transcript about {job['topic']}. It contains sample content to demonstrate how the frontend displays transcripts. The podcast discusses various aspects of the topic in an engaging and informative manner."
        job["metrics"] = {
            "duration_seconds": 180,
            "word_count": 250,
            "average_speaking_rate": 150
        }
    
    # Return the exact format expected by frontend
    result_data = {
        "id": job["id"],
        "topic": job["topic"],
        "status": job["status"],
        "progress": job["progress"],
        "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(job["created_at"])),
        "completed_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(job["completed_at"])) if job["completed_at"] else None,
        "audio_url": job["audio_url"],
        "transcript": job["transcript"],
        "metrics": job["metrics"],
        "error": job["error"]
    }
    
    logger.info(f"📋 [MOCK] Returning mock result for {job_id}:")
    logger.info(f"📋 [MOCK] Status: {result_data['status']}, Progress: {result_data['progress']}%")
    logger.info(f"📋 [MOCK] Full data: {json.dumps(result_data, indent=2)}")
    
    return result_data


@router.get("/mock/audio/sample.mp3")
async def mock_audio_file():
    """
    MOCK: Serve a mock audio file.
    Returns a simple response since we don't have actual audio.
    """
    logger.info("🎭 [MOCK] Mock audio file requested")
    return {"message": "Mock audio file - in a real implementation this would be an MP3 file"}


@router.post("/generate")
async def generate_podcast(request: GenerateRequest):
    """
    Generate a new podcast from the given request.
    
    This endpoint starts the podcast generation process asynchronously.
    Returns immediately with a job ID that can be used to track progress.
    """
    request_id = f"req_{int(time.time() * 1000)}"
    
    try:
        logger.info(f"🚀 [DEBUG] [{request_id}] Received podcast generation request")
        logger.info(f"📝 [DEBUG] [{request_id}] Request data: {request.model_dump()}")
        logger.info(f"🎯 [DEBUG] [{request_id}] Topic: '{request.topic}'")
        
        # Check if podcast generator is ready
        logger.info(f"🔧 [DEBUG] [{request_id}] Checking podcast generator readiness...")
        
        # Start podcast generation
        logger.info(f"⚡ [DEBUG] [{request_id}] Starting podcast generation...")
        result = await podcast_generator.generate_podcast(request)
        
        logger.info(f"✅ [DEBUG] [{request_id}] Successfully started podcast generation")
        logger.info(f"🆔 [DEBUG] [{request_id}] Job ID: {result.job_id}")
        
        # Return simple dict response
        response = {"id": result.job_id}
        logger.info(f"📤 [DEBUG] [{request_id}] Returning response: {response}")
        
        return response
        
    except Exception as e:
        logger.error(f"💥 [DEBUG] [{request_id}] Failed to start podcast generation")
        logger.error(f"❌ [DEBUG] [{request_id}] Error type: {type(e).__name__}")
        logger.error(f"❌ [DEBUG] [{request_id}] Error message: {str(e)}")
        logger.error(f"❌ [DEBUG] [{request_id}] Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get the result of a specific job."""
    try:
        logger.info(f"🔍 [DEBUG] Getting result for job ID: {job_id}")
        
        status = await podcast_generator.get_job_status(job_id)
        if not status:
            logger.warning(f"⚠️ [DEBUG] Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Handle both dict and object responses
        if isinstance(status, dict):
            logger.info(f"📊 [DEBUG] Job status for {job_id}: {status.get('status', 'unknown')}")
            logger.info(f"📈 [DEBUG] Job progress for {job_id}: {status.get('progress', 0)}%")
            
            # Extract progress percentage if it's an object
            progress_value = status.get('progress', 0)
            if isinstance(progress_value, dict) and 'percent' in progress_value:
                progress_value = progress_value['percent']
            elif hasattr(progress_value, 'percent'):
                progress_value = progress_value.percent
            elif not isinstance(progress_value, (int, float)):
                progress_value = 0
            
            result_data = {
                "id": job_id,
                "topic": status.get('topic', ''),
                "status": status.get('status', 'unknown'),
                "progress": progress_value,
                "created_at": status.get('created_at', ''),
                "completed_at": status.get('completed_at', None),
                "audio_url": status.get('audio_url', None),
                "transcript": status.get('transcript', None),
                "metrics": status.get('metrics', None),
                "error": status.get('error', None)
            }
        else:
            logger.info(f"📊 [DEBUG] Job status for {job_id}: {status.status}")
            logger.info(f"📈 [DEBUG] Job progress for {job_id}: {status.progress}%")
            logger.info(f"🔍 [DEBUG] Job has result: {hasattr(status, 'result') and status.result is not None}")
            if hasattr(status, 'result') and status.result:
                logger.info(f"🎯 [DEBUG] Result status: {status.result.status}")
                logger.info(f"🎯 [DEBUG] Result mp3_url: {status.result.mp3_url}")
            
            # Extract progress percentage if it's an object
            progress_value = status.progress
            if isinstance(progress_value, dict) and 'percent' in progress_value:
                progress_value = progress_value['percent']
            elif hasattr(progress_value, 'percent'):
                progress_value = progress_value.percent
            elif not isinstance(progress_value, (int, float)):
                progress_value = 0
            
            # Convert datetime objects to ISO strings
            created_at = status.created_at.isoformat() if hasattr(status, 'created_at') and status.created_at else ''
            completed_at = status.completed_at.isoformat() if hasattr(status, 'completed_at') and status.completed_at else None
            
            result_data = {
                "id": job_id,
                "topic": getattr(status, 'topic', ''),
                "status": status.status,
                "progress": progress_value,
                "created_at": created_at,
                "completed_at": completed_at,
            }
            
            # Add additional fields if job is completed
            logger.info(f"🔄 [DEBUG] Checking completion status for {job_id}")
            logger.info(f"🔄 [DEBUG] status.status == 'completed': {status.status == 'completed'}")
            logger.info(f"🔄 [DEBUG] hasattr(status, 'result'): {hasattr(status, 'result')}")
            logger.info(f"🔄 [DEBUG] status.result: {status.result}")
            logger.info(f"🔄 [DEBUG] status.result is not None: {status.result is not None}")
            if hasattr(status, 'result') and status.result:
                logger.info(f"🔄 [DEBUG] hasattr(status.result, 'mp3_url'): {hasattr(status.result, 'mp3_url')}")
                logger.info(f"🔄 [DEBUG] status.result.mp3_url: {getattr(status.result, 'mp3_url', 'NO ATTR')}")
            
            if status.status == "completed" and hasattr(status, 'result') and status.result and hasattr(status.result, 'mp3_url') and status.result.mp3_url:
                logger.info(f"🚀 [DEBUG] Processing completed job result for {job_id}")
                # Read the generated script as transcript
                transcript_content = None
                if hasattr(status.result, 'script_url') and status.result.script_url:
                    try:
                        script_path = status.result.script_url.replace('/api/v1/static/scripts/', 'static/scripts/')
                        if os.path.exists(script_path):
                            with open(script_path, 'r', encoding='utf-8') as f:
                                transcript_content = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read script file: {e}")
                
                result_data.update({
                    "audio_url": str(status.result.mp3_url) if status.result.mp3_url else None,
                    "transcript": transcript_content,
                    "metrics": {
                        "duration_seconds": status.result.metrics.duration_seconds if status.result.metrics else 0,
                        "word_count": status.result.metrics.word_count if status.result.metrics else 0,
                        "average_speaking_rate": getattr(status.result.metrics, 'average_speaking_rate', 0) if status.result.metrics else 0,
                    } if status.result.metrics else None
                })
                logger.info(f"✅ [DEBUG] Added result data: audio_url={result_data.get('audio_url')}")
            elif status.status == "completed":
                # Fallback: Try to find files directly on filesystem
                logger.info(f"🔄 [DEBUG] Job {job_id} completed but no result object, trying filesystem fallback")
                
                base_url = "http://localhost:8000"
                
                # Check for generated files
                podcast_file = f"static/podcasts/podcast_{job_id}.mp3"
                script_file = f"static/scripts/script_{job_id}.txt"
                notes_file = f"static/notes/notes_{job_id}.md"
                
                transcript_content = None
                metrics = None
                audio_url = None
                
                if os.path.exists(podcast_file):
                    audio_url = f"{base_url}/api/v1/static/podcasts/podcast_{job_id}.mp3"
                    logger.info(f"✅ [DEBUG] Found audio file: {podcast_file}")
                
                if os.path.exists(script_file):
                    try:
                        with open(script_file, 'r', encoding='utf-8') as f:
                            transcript_content = f.read()
                        
                        # Calculate basic metrics from transcript
                        word_count = len(transcript_content.split())
                        # Estimate duration: ~150 words per minute for speech
                        estimated_duration = (word_count / 150) * 60
                        
                        metrics = {
                            "duration_seconds": estimated_duration,
                            "word_count": word_count,
                            "average_speaking_rate": 150
                        }
                        logger.info(f"✅ [DEBUG] Read transcript: {word_count} words")
                    except Exception as e:
                        logger.warning(f"Could not read script file: {e}")
                
                result_data.update({
                    "audio_url": audio_url,
                    "transcript": transcript_content,
                    "metrics": metrics
                })
                logger.info(f"✅ [DEBUG] Fallback result data: audio_url={audio_url}")
            else:
                logger.warning(f"⚠️ [DEBUG] Job {job_id} completed but no result available")
            
            # Add error if job failed
            if status.status == "failed":
                result_data["error"] = getattr(status, 'error', 'Unknown error')
        
        logger.info(f"📋 [DEBUG] Returning result data for {job_id}")
        return result_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [DEBUG] Failed to get result for job {job_id}")
        logger.error(f"❌ [DEBUG] Error type: {type(e).__name__}")
        logger.error(f"❌ [DEBUG] Error message: {str(e)}")
        logger.error(f"❌ [DEBUG] Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a specific job."""
    try:
        status = await podcast_generator.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    try:
        success = await podcast_generator.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel job")
        
        return {"message": "Job cancelled successfully", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of jobs to return")
):
    """List all jobs with optional filtering."""
    try:
        if status:
            # Filter by status
            from app.services.job_queue import JobState
            try:
                job_state = JobState(status)
                jobs = await job_queue.get_jobs_by_status(job_state, limit)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        else:
            # Get all jobs
            jobs = await podcast_generator.get_all_jobs(limit)
        
        return jobs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/stats")
async def get_queue_stats():
    """Get queue statistics and health information."""
    try:
        stats = await podcast_generator.get_queue_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/static/podcasts/{filename}")
async def serve_podcast(filename: str):
    """Serve generated podcast files."""
    try:
        file_path = f"static/podcasts/{filename}"
        
        # Check if file exists
        import os
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Podcast file not found")
        
        return FileResponse(
            file_path,
            media_type="audio/mpeg",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve podcast file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/static/notes/{filename}")
async def serve_notes(filename: str):
    """Serve generated notes files."""
    try:
        file_path = f"static/notes/{filename}"
        
        # Check if file exists
        import os
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Notes file not found")
        
        return FileResponse(
            file_path,
            media_type="text/markdown",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve notes file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/static/scripts/{filename}")
async def serve_script(filename: str):
    """Serve generated script files."""
    try:
        file_path = f"static/scripts/{filename}"
        
        # Check if file exists
        import os
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Script file not found")
        
        return FileResponse(
            file_path,
            media_type="text/plain",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve script file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("🏥 [DEBUG] Health check requested")
    
    try:
        # Check if services are working
        logger.info("🔧 [DEBUG] Checking podcast generator...")
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "podcast-generator-api",
            "version": "1.0.0"
        }
        
        logger.info(f"✅ [DEBUG] Health check successful: {health_data}")
        return health_data
        
    except Exception as e:
        logger.error(f"💥 [DEBUG] Health check failed: {e}")
        logger.error(f"❌ [DEBUG] Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@router.get("/providers/llm")
async def get_llm_providers():
    """Get available LLM providers."""
    try:
        # This would return configured providers
        providers = []
        
        if podcast_generator.llm_provider:
            providers.append({
                "name": podcast_generator.llm_provider.__class__.__name__,
                "status": "configured"
            })
        
        return {"providers": providers}
        
    except Exception as e:
        logger.error(f"Failed to get LLM providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/tts")
async def get_tts_providers():
    """Get available TTS providers."""
    try:
        # This would return configured providers
        providers = []
        
        if podcast_generator.tts_provider:
            providers.append({
                "name": podcast_generator.tts_provider.__class__.__name__,
                "status": "configured"
            })
        
        return {"providers": providers}
        
    except Exception as e:
        logger.error(f"Failed to get TTS providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def get_available_voices():
    """Get available TTS voices."""
    try:
        voices = await podcast_generator.tts_provider.get_available_voices()
        return {"voices": voices}
        
    except Exception as e:
        logger.error(f"Failed to get available voices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 