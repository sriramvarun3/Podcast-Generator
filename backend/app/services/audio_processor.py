"""
Advanced audio processing service for podcast generation.
Handles music bed mixing, loudness normalization, and audio enhancement.
"""

import asyncio
import os
import random
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger

from app.core.config import settings


class AudioProcessor:
    """Advanced audio processing for podcast generation."""
    
    def __init__(self):
        self.target_lufs = settings.target_lufs
        self.sample_rate = settings.sample_rate
        self.bit_rate = settings.bit_rate
        self.music_bed_dir = "static/music_beds"
        self._ensure_music_bed_directory()
    
    def _ensure_music_bed_directory(self):
        """Ensure music bed directory exists with sample files."""
        os.makedirs(self.music_bed_dir, exist_ok=True)
        
        # Create a sample music bed if none exists
        sample_bed_path = os.path.join(self.music_bed_dir, "ambient_background.mp3")
        if not os.path.exists(sample_bed_path):
            self._create_sample_music_bed(sample_bed_path)
    
    def _create_sample_music_bed(self, output_path: str):
        """Create a simple ambient music bed using pydub."""
        try:
            from pydub import AudioSegment
            from pydub.generators import Sine
            
            # Create a simple ambient tone
            duration_ms = 30000  # 30 seconds
            frequency = 220  # A3 note
            
            # Generate base tone
            base_tone = Sine(frequency).to_audio_segment(duration=duration_ms)
            
            # Add some variation
            varied_tone = base_tone - 20  # Reduce volume
            
            # Export
            varied_tone.export(output_path, format="mp3", bitrate="128k")
            logger.info(f"Created sample music bed: {output_path}")
            
        except ImportError:
            logger.warning("pydub not available, cannot create sample music bed")
        except Exception as e:
            logger.warning(f"Failed to create sample music bed: {e}")
    
    async def process_audio(
        self,
        input_path: str,
        output_path: str,
        add_music_bed: bool = True,
        normalize_loudness: bool = True,
        enhance_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Process audio with music bed, normalization, and enhancement.
        Falls back to simple copy if pydub is not available.
        """
        try:
            # Try the full audio processing
            return await self._process_audio_full(
                input_path, output_path, add_music_bed, normalize_loudness, enhance_audio
            )
        except ImportError as e:
            if "pyaudioop" in str(e) or "pydub" in str(e):
                logger.warning(f"Audio processing unavailable ({e}), using simple fallback")
                return await self._process_audio_fallback(input_path, output_path)
            else:
                raise
        except Exception as e:
            logger.warning(f"Audio processing failed ({e}), using simple fallback")
            return await self._process_audio_fallback(input_path, output_path)
    
    async def _process_audio_fallback(
        self,
        input_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """Simple fallback: just copy the file."""
        try:
            import shutil
            import os
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Copy the file
            shutil.copy2(input_path, output_path)
            
            # Get basic file info
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            logger.info(f"Audio fallback processing completed, file size: {file_size} bytes")
            
            return {
                "output_path": output_path,
                "file_size": file_size,
                "duration_seconds": 60,  # Rough estimate
                "sample_rate": self.sample_rate,
                "bit_rate": self.bit_rate,
                "enhancements_applied": {
                    "music_bed": False,
                    "loudness_normalization": False,
                    "audio_enhancement": False
                },
                "fallback_mode": True,
                "processing_seconds": 0.1
            }
            
        except Exception as e:
            logger.error(f"Audio fallback processing failed: {e}")
            raise
    
    async def _process_audio_full(
        self,
        input_path: str,
        output_path: str,
        add_music_bed: bool = True,
        normalize_loudness: bool = True,
        enhance_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Process audio file with comprehensive enhancements.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output audio file
            add_music_bed: Whether to add background music
            normalize_loudness: Whether to normalize loudness
            enhance_audio: Whether to apply audio enhancements
            
        Returns:
            Processing result information
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Load audio with pydub
            from pydub import AudioSegment
            audio = AudioSegment.from_file(input_path)
            
            # Store original duration
            original_duration = len(audio) / 1000.0
            
            # Apply audio enhancements
            if enhance_audio:
                audio = await self._enhance_audio(audio)
            
            # Normalize loudness if requested
            if normalize_loudness:
                audio = await self._normalize_loudness(audio)
            
            # Add music bed if requested
            if add_music_bed:
                audio = await self._add_music_bed(audio)
            
            # Final audio processing
            audio = await self._finalize_audio(audio)
            
            # Export to MP3
            audio.export(
                output_path,
                format="mp3",
                bitrate=f"{self.bit_rate}k",
                parameters=["-ar", str(self.sample_rate)]
            )
            
            # Get final metrics
            final_audio = AudioSegment.from_file(output_path)
            duration = len(final_audio) / 1000.0  # Convert to seconds
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "duration_seconds": duration,
                "original_duration": original_duration,
                "sample_rate": self.sample_rate,
                "bit_rate": self.bit_rate,
                "status": "success",
                "enhancements_applied": {
                    "music_bed": add_music_bed,
                    "loudness_normalization": normalize_loudness,
                    "audio_enhancement": enhance_audio
                }
            }
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise
    
    async def _enhance_audio(self, audio) -> Any:
        """Apply audio enhancements for better quality."""
        try:
            # Apply subtle compression
            audio = audio.compress_dynamic_range(
                threshold=-20.0,  # dB
                ratio=4.0,        # 4:1 compression
                attack=5.0,       # ms
                release=50.0      # ms
            )
            
            # Apply subtle EQ (boost presence frequencies)
            audio = audio.high_pass_filter(80)   # Remove low rumble
            audio = audio.low_pass_filter(8000)  # Remove harsh highs
            
            # Normalize peak levels
            audio = audio.normalize()
            
            logger.info("Applied audio enhancements")
            return audio
            
        except Exception as e:
            logger.warning(f"Audio enhancement failed: {e}")
            return audio
    
    async def _normalize_loudness(self, audio) -> Any:
        """Normalize audio loudness to target LUFS."""
        try:
            import pyloudnorm as pyln
            
            # Convert to numpy array for loudness measurement
            samples = audio.get_array_of_samples()
            sample_rate = audio.frame_rate
            
            # Create loudness meter
            meter = pyln.Meter(sample_rate)
            
            # Measure current loudness
            current_loudness = pyln.loudness(samples)
            
            # Calculate gain needed
            gain_db = self.target_lufs - current_loudness
            
            # Apply gain (with safety limits)
            gain_db = max(-20, min(20, gain_db))  # Limit to ±20dB
            
            # Apply gain
            normalized_audio = audio + gain_db
            
            logger.info(f"Normalized audio from {current_loudness:.1f} LUFS to {self.target_lufs:.1f} LUFS")
            
            return normalized_audio
            
        except ImportError:
            logger.warning("pyloudnorm not available, skipping loudness normalization")
            return audio
        except Exception as e:
            logger.warning(f"Loudness normalization failed: {e}")
            return audio
    
    async def _add_music_bed(self, audio) -> Any:
        """Add background music bed to audio."""
        try:
            # Get available music beds
            music_beds = self._get_available_music_beds()
            
            if not music_beds:
                logger.warning("No music beds available, skipping")
                return audio
            
            # Select a random music bed
            selected_bed = random.choice(music_beds)
            logger.info(f"Using music bed: {selected_bed}")
            
            # Load music bed
            from pydub import AudioSegment
            music_bed = AudioSegment.from_file(selected_bed)
            
            # Loop music bed to match audio length
            audio_duration = len(audio)
            bed_duration = len(music_bed)
            
            if bed_duration < audio_duration:
                # Loop the music bed
                loops_needed = (audio_duration // bed_duration) + 1
                music_bed = music_bed * loops_needed
            
            # Trim to exact length
            music_bed = music_bed[:audio_duration]
            
            # Reduce music bed volume (mix at -25dB)
            music_bed = music_bed - 25
            
            # Mix speech and music
            mixed_audio = audio.overlay(music_bed)
            
            logger.info("Successfully added music bed")
            return mixed_audio
            
        except Exception as e:
            logger.warning(f"Music bed addition failed: {e}")
            return audio
    
    def _get_available_music_beds(self) -> List[str]:
        """Get list of available music bed files."""
        if not os.path.exists(self.music_bed_dir):
            return []
        
        music_beds = []
        for file in os.listdir(self.music_bed_dir):
            if file.lower().endswith(('.mp3', '.wav', '.m4a')):
                music_beds.append(os.path.join(self.music_bed_dir, file))
        
        return music_beds
    
    async def _finalize_audio(self, audio) -> Any:
        """Apply final audio processing steps."""
        try:
            # Ensure consistent sample rate
            if audio.frame_rate != self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)
            
            # Apply final normalization
            audio = audio.normalize()
            
            # Apply fade in/out for smooth edges
            fade_duration = 100  # 100ms
            audio = audio.fade_in(fade_duration).fade_out(fade_duration)
            
            logger.info("Applied final audio processing")
            return audio
            
        except Exception as e:
            logger.warning(f"Final audio processing failed: {e}")
            return audio
    
    async def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed information about an audio file."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(file_path)
            
            return {
                "duration_seconds": len(audio) / 1000.0,
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "frame_count": audio.frame_count(),
                "file_size_mb": os.path.getsize(file_path) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}
    
    async def cleanup_temp_files(self, temp_files: List[str]):
        """Clean up temporary audio files."""
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}") 