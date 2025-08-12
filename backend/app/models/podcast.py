"""
Pydantic models for podcast generation.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class GenerateRequest(BaseModel):
    """Request model for podcast generation."""
    
    topic: str = Field(..., min_length=1, max_length=500, description="Main topic for the podcast")
    description: str = Field(default="", max_length=2000, description="Optional description or context")
    tone: Literal["funny", "factual", "serious", "humorous", "neutral"] = Field(
        default="neutral", description="Tone of the podcast"
    )
    length: Literal[5, 10, 15] = Field(
        default=10, description="Target length in minutes"
    )


class Source(BaseModel):
    """Source information for podcast content."""
    
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Source title")
    domain: str = Field(..., description="Source domain")
    content_length: int = Field(..., description="Length of extracted content")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


class ProgressUpdate(BaseModel):
    """Progress update for podcast generation."""
    
    stage: int = Field(..., ge=0, description="Current stage number")
    message: str = Field(..., description="Human-readable stage message")
    percent: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    log: List[str] = Field(default_factory=list, description="Activity log entries")
    estimated_remaining: Optional[int] = Field(None, ge=0, description="Estimated seconds remaining")


class PodcastMetrics(BaseModel):
    """Metrics about the generated podcast."""
    
    sources_used: int = Field(..., ge=0, description="Number of sources used")
    sources: List[Source] = Field(default_factory=list, description="List of sources used")
    duration_seconds: float = Field(..., ge=0, description="Final duration in seconds")
    word_count: int = Field(..., ge=0, description="Word count of the script")
    lufs: float = Field(..., description="Final loudness in LUFS")
    tts_seconds: float = Field(..., description="Time spent on TTS generation")
    processing_seconds: float = Field(..., description="Total processing time")
    audio_quality: Literal["low", "medium", "high"] = Field(..., description="Audio quality setting")


class PodcastResult(BaseModel):
    """Result of podcast generation."""
    
    status: Literal["ready", "error", "running"] = Field(..., description="Generation status")
    job_id: str = Field(..., description="Unique job identifier")
    title: Optional[str] = Field(None, description="Generated podcast title")
    mp3_url: Optional[str] = Field(None, description="URL to download the MP3")
    notes_url: Optional[str] = Field(None, description="URL to view show notes")
    script_url: Optional[str] = Field(None, description="URL to view the script")
    metrics: Optional[PodcastMetrics] = Field(None, description="Generation metrics")
    error: Optional[str] = Field(None, description="Error message if status is error")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")


class JobStatus(BaseModel):
    """Job status information."""
    
    job_id: str = Field(..., description="Unique job identifier")
    topic: str = Field(..., description="Topic of the podcast")
    status: Literal["pending", "running", "completed", "failed", "canceled"] = Field(
        ..., description="Current job status"
    )
    progress: Optional[ProgressUpdate] = Field(None, description="Current progress")
    result: Optional[PodcastResult] = Field(None, description="Final result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class CancelRequest(BaseModel):
    """Request to cancel a job."""
    
    job_id: str = Field(..., description="Job ID to cancel")


class CancelResponse(BaseModel):
    """Response to cancel request."""
    
    ok: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Cancellation result message") 