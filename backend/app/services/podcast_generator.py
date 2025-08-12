"""
Main podcast generation service that orchestrates the entire process.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from loguru import logger

from app.core.config import settings
from app.services.web_search import WebSearchService
from app.services.content_extractor import ContentExtractor
from app.services.llm_provider import LLMProviderFactory
from app.services.tts_provider import TTSProviderFactory
from app.services.audio_processor import AudioProcessor
from app.services.job_queue import job_queue
from app.models.podcast import (
    GenerateRequest, PodcastResult, PodcastMetrics, Source, ProgressUpdate
)


class PodcastGenerator:
    """Main service for generating podcasts."""
    
    def __init__(self):
        self.web_search = WebSearchService()
        self.content_extractor = ContentExtractor()
        self.audio_processor = AudioProcessor()
        
        # Initialize providers
        try:
            self.llm_provider = LLMProviderFactory.create_provider()
            self.tts_provider = TTSProviderFactory.create_provider()
        except Exception as e:
            logger.warning(f"Failed to initialize providers: {e}")
            logger.warning("Providers will be initialized when needed")
            self.llm_provider = None
            self.tts_provider = None
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            settings.static_dir,
            settings.upload_dir,
            "static/podcasts",
            "static/notes",
            "static/scripts",
            "static/music_beds"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    async def _ensure_providers_initialized(self):
        """Ensure LLM and TTS providers are initialized."""
        if self.llm_provider is None:
            try:
                self.llm_provider = LLMProviderFactory.create_provider()
                logger.info("LLM provider initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize LLM provider: {e}")
                raise ValueError("LLM provider not available")
        
        if self.tts_provider is None:
            try:
                self.tts_provider = TTSProviderFactory.create_provider()
                logger.info("TTS provider initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize TTS provider: {e}")
                raise ValueError("TTS provider not available")
    
    async def generate_podcast(
        self,
        request: GenerateRequest,
        progress_callback=None
    ) -> PodcastResult:
        """
        Generate a complete podcast from the request.
        
        Args:
            request: Podcast generation request
            progress_callback: Optional callback for progress updates
            
        Returns:
            Generated podcast result
        """
        # Ensure providers are initialized
        await self._ensure_providers_initialized()
        
        # Create job in queue
        job_id = await job_queue.create_job(
            topic=request.topic,
            description=request.description,
            tone=request.tone,
            target_length=request.length,
            progress_callback=progress_callback
        )
        
        # Start job in background
        await job_queue.start_job(job_id, self._generate_podcast_worker)
        
        # Return immediate response
        return PodcastResult(
            status="running",
            job_id=job_id,
            created_at=datetime.utcnow()
        )
    
    async def _generate_podcast_worker(self, job_id: str) -> PodcastResult:
        """
        Worker function that actually generates the podcast.
        This runs in the background via the job queue.
        """
        start_time = datetime.utcnow()
        temp_files = []
        
        try:
            # Get job details
            job = job_queue.jobs.get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            request = GenerateRequest(
                topic=job.topic,
                description=job.description,
                tone=job.tone,
                target_length=job.target_length
            )
            
            logger.info(f"Starting podcast generation for job {job_id}: {request.topic}")
            
            # Stage 1: Web Search
            await job_queue._update_job_progress(job_id, 0, "Searching the web for diverse sources...")
            sources = await self.web_search.get_diverse_sources(request.topic, request.description)
            
            if not sources:
                # Fallback mode: Generate content based on topic only
                logger.warning(f"No web sources found for '{request.topic}', using fallback content generation")
                await job_queue._update_job_progress(job_id, 15, "No web sources found, generating content from topic...")
                
                # Create fallback content
                fallback_content = f"""
                Topic: {request.topic}
                
                This is a generated podcast about {request.topic}. While we couldn't find specific web sources 
                for this topic, here's some general information and discussion points:
                
                {request.description if request.description else f"An exploration of {request.topic}, covering its key aspects, significance, and relevance."}
                
                Key Discussion Points:
                - Background and context of {request.topic}
                - Why {request.topic} is important and relevant today
                - Different perspectives and viewpoints on {request.topic}
                - Future implications and developments related to {request.topic}
                
                This podcast aims to provide an informative and engaging discussion about {request.topic}, 
                even without access to current web sources.
                """
                
                extracted_content = fallback_content
                await job_queue._update_job_progress(job_id, 30, "Generated fallback content successfully")
            else:
                await job_queue._update_job_progress(job_id, 15, f"Found {len(sources)} relevant sources")
                
                # Stage 2: Content Extraction
                await job_queue._update_job_progress(job_id, 20, "Extracting and cleaning content from sources...")
                extracted_content = await self.content_extractor.extract_content_from_sources(sources)
                await job_queue._update_job_progress(job_id, 30, "Content extraction completed")
            
            # Progress update - handle both string (fallback) and list (web sources) content
            if isinstance(extracted_content, str):
                content_description = "fallback content"
            else:
                content_description = f"{len(extracted_content)} sources"
            
            await job_queue._update_job_progress(job_id, 35, f"Extracted content from {content_description}")
            
            # Stage 3: Script Generation
            await job_queue._update_job_progress(job_id, 50, "Generating podcast script using AI...")
            
            # Handle different content formats for LLM
            if isinstance(extracted_content, str):
                # For fallback mode, we pass the string directly as content
                script_result = await self.llm_provider.generate_script_from_text(
                    topic=request.topic,
                    description=request.description,
                    tone=request.tone,
                    target_length=request.length,
                    content_text=extracted_content
                )
            else:
                # For web sources, use the normal method
                script_result = await self.llm_provider.generate_script(
                    topic=request.topic,
                    description=request.description,
                    tone=request.tone,
                    target_length=request.length,
                    extracted_content=extracted_content
                )
            
            script = script_result["script"]
            word_count = script_result["word_count"]
            
            await job_queue._update_job_progress(job_id, 65, "Script generated successfully")
            
            # Stage 4: Text-to-Speech
            await job_queue._update_job_progress(job_id, 70, "Converting script to speech...")
            
            # Save script to file
            script_filename = f"script_{job_id}.txt"
            script_path = f"static/scripts/{script_filename}"
            
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)
            
            # Generate speech
            speech_filename = f"speech_{job_id}.mp3"
            speech_path = f"static/podcasts/{speech_filename}"
            temp_files.append(speech_path)
            
            tts_result = await self.tts_provider.generate_speech(
                script=script,
                output_path=speech_path
            )
            
            await job_queue._update_job_progress(job_id, 80, "Speech generation completed")
            
            # Stage 5: Audio Processing
            await job_queue._update_job_progress(job_id, 85, "Processing and enhancing audio...")
            
            final_filename = f"podcast_{job_id}.mp3"
            final_path = f"static/podcasts/{final_filename}"
            
            audio_result = await self.audio_processor.process_audio(
                input_path=speech_path,
                output_path=final_path,
                add_music_bed=True,
                normalize_loudness=True,
                enhance_audio=True
            )
            
            await job_queue._update_job_progress(job_id, 95, "Audio processing completed")
            
            # Stage 6: Generate Notes
            await job_queue._update_job_progress(job_id, 98, "Generating show notes...")
            
            notes_filename = f"notes_{job_id}.md"
            notes_path = f"static/notes/{notes_filename}"
            
            notes_content = await self._generate_notes(
                request, sources, extracted_content, script, audio_result
            )
            
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(notes_content)
            
            await job_queue._update_job_progress(job_id, 100, "Podcast generation completed!")
            
            # Calculate metrics
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Handle metrics for different content types
            if isinstance(extracted_content, str):
                sources_used = 0
                sources_list = []
            else:
                sources_used = len(extracted_content)
                sources_list = sources
            
            metrics = PodcastMetrics(
                sources_used=sources_used,
                sources=sources_list,
                duration_seconds=audio_result["duration_seconds"],
                word_count=word_count,
                lufs=settings.target_lufs,
                tts_seconds=tts_result.get("processing_time", 0),
                processing_seconds=processing_time,
                audio_quality="high"
            )
            
            # Create result
            base_url = "http://localhost:8000"  # TODO: Get from settings
            result = PodcastResult(
                status="ready",
                job_id=job_id,
                title=f"Podcast: {request.topic}",
                mp3_url=f"{base_url}/api/v1/static/podcasts/{final_filename}",
                notes_url=f"{base_url}/api/v1/static/notes/{notes_filename}",
                script_url=f"{base_url}/api/v1/static/scripts/{script_filename}",
                metrics=metrics,
                created_at=start_time,
                completed_at=end_time
            )
            
            # Clean up temporary files
            await self.audio_processor.cleanup_temp_files(temp_files)
            
            logger.info(f"Podcast generation completed successfully for job {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Podcast generation failed for job {job_id}: {e}")
            
            # Clean up any generated files
            await self._cleanup_files(job_id)
            await self.audio_processor.cleanup_temp_files(temp_files)
            
            return PodcastResult(
                status="error",
                job_id=job_id,
                error=str(e),
                created_at=start_time
            )
    
    async def _generate_notes(
        self,
        request: GenerateRequest,
        sources: List[Source],
        extracted_content: List[Dict[str, Any]],
        script: str,
        audio_result: Dict[str, Any]
    ) -> str:
        """Generate show notes in Markdown format."""
        
        notes = f"""# Show Notes: {request.topic}

## Episode Details
- **Topic**: {request.topic}
- **Description**: {request.description or "No additional description provided"}
- **Tone**: {request.tone}
- **Target Length**: {request.length} minutes
- **Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

## Audio Information
- **Duration**: {audio_result.get('duration_seconds', 0):.1f} seconds
- **Sample Rate**: {audio_result.get('sample_rate', 0)} Hz
- **Bit Rate**: {audio_result.get('bit_rate', 0)} kbps
- **Format**: MP3
- **Enhancements**: {', '.join([k for k, v in audio_result.get('enhancements_applied', {}).items() if v])}

## Sources Used
"""
        
        for i, source in enumerate(sources, 1):
            notes += f"""
### {i}. {source.title}
- **URL**: {source.url}
- **Domain**: {source.domain}
- **Relevance Score**: {source.relevance_score:.2f}
"""
        
        notes += f"""
## Content Summary
This episode covers the following key points based on research from {len(sources)} diverse sources:

"""
        
        # Add key points from the script
        script_lines = script.split('\n')
        key_points = [line.strip() for line in script_lines if line.strip() and not line.startswith('#')]
        
        for i, point in enumerate(key_points[:10], 1):  # Limit to first 10 points
            notes += f"{i}. {point}\n"
        
        notes += f"""
## Technical Details
- **Word Count**: {len(script.split())}
- **Processing Time**: {audio_result.get('processing_seconds', 0):.1f} seconds
- **Audio Quality**: High quality MP3 with normalized loudness and music bed

---
*This podcast was automatically generated using AI technology. Please verify any facts or claims mentioned.*
"""
        
        return notes
    
    async def _cleanup_files(self, job_id: str):
        """Clean up generated files for a failed job."""
        try:
            files_to_remove = [
                f"static/podcasts/speech_{job_id}.mp3",
                f"static/podcasts/podcast_{job_id}.mp3",
                f"static/notes/notes_{job_id}.md",
                f"static/scripts/script_{job_id}.txt"
            ]
            
            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up file: {file_path}")
                    
        except Exception as e:
            logger.warning(f"Failed to cleanup files for job {job_id}: {e}")
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a specific job."""
        status = await job_queue.get_job_status(job_id)
        if status:
            return status.dict()
        return {
            "job_id": job_id,
            "status": "unknown",
            "message": "Job not found"
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        return await job_queue.cancel_job(job_id)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return await job_queue.get_queue_stats()
    
    async def get_all_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all jobs."""
        jobs = await job_queue.get_all_jobs(limit)
        return [job.dict() for job in jobs if job] 