"""
Main FastAPI application entry point.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.api.routes import router

# Configure logging
logger.add(
    "logs/app.log",
    rotation="1 day",
    retention="7 days",
    level=settings.log_level,
    format="{time} | {level} | {message}"
)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered podcast generator with web search, content extraction, and TTS",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(router)

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "message": "Podcast Generator API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Server running on {settings.host}:{settings.port}")
    
    # Ensure required directories exist
    directories = [
        "static",
        "static/podcasts",
        "static/notes",
        "static/scripts",
        "static/music_beds",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")
    
    # Start job queue cleanup task
    from app.services.job_queue import job_queue
    await job_queue.ensure_cleanup_task_running()
    logger.info("Job queue cleanup task started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Podcast Generator API")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    ) 