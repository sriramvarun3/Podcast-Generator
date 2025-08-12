"""
Text-to-Speech provider service with support for multiple TTS engines.
"""

import asyncio
import os
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from loguru import logger

from app.core.config import settings


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""
    
    @abstractmethod
    async def generate_speech(
        self,
        script: str,
        output_path: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate speech from text script."""
        pass
    
    @abstractmethod
    async def get_available_voices(self) -> list:
        """Get list of available voices."""
        pass


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS provider."""
    
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
    
    async def generate_speech(
        self,
        script: str,
        output_path: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate speech using ElevenLabs API."""
        try:
            import httpx
            
            # Prepare request
            voice_id = voice_settings.get("voice_id", self.default_voice_id) if voice_settings else self.default_voice_id
            
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": script,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": voice_settings.get("stability", 0.5) if voice_settings else 0.5,
                    "similarity_boost": voice_settings.get("similarity_boost", 0.5) if voice_settings else 0.5
                }
            }
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                
                # Save audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"ElevenLabs TTS completed in {processing_time:.2f}s")
            
            return {
                "provider": "elevenlabs",
                "output_path": output_path,
                "processing_time": processing_time,
                "voice_id": voice_id,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            raise
    
    async def get_available_voices(self) -> list:
        """Get available voices from ElevenLabs."""
        try:
            import httpx
            
            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                voices_data = response.json()
                voices = []
                
                for voice in voices_data.get("voices", []):
                    voices.append({
                        "id": voice["voice_id"],
                        "name": voice["name"],
                        "category": voice.get("category", "unknown"),
                        "description": voice.get("description", "")
                    })
                
                return voices
                
        except Exception as e:
            logger.error(f"Failed to get ElevenLabs voices: {e}")
            return []


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider."""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1/audio/speech"
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
    
    async def generate_speech(
        self,
        script: str,
        output_path: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate speech using OpenAI TTS API."""
        try:
            import httpx
            
            # Prepare request
            voice = voice_settings.get("voice", "alloy") if voice_settings else "alloy"
            model = voice_settings.get("model", "tts-1") if voice_settings else "tts-1"
            
            url = self.base_url
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "input": script,
                "voice": voice,
                "response_format": "mp3",
                "speed": voice_settings.get("speed", 1.0) if voice_settings else 1.0
            }
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                
                # Save audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"OpenAI TTS completed in {processing_time:.2f}s")
            
            return {
                "provider": "openai",
                "output_path": output_path,
                "processing_time": processing_time,
                "voice": voice,
                "model": model,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"OpenAI TTS failed: {e}")
            raise
    
    async def get_available_voices(self) -> list:
        """Get available voices from OpenAI."""
        return [
            {"id": "alloy", "name": "Alloy", "description": "A balanced, versatile voice"},
            {"id": "echo", "name": "Echo", "description": "A warm, friendly voice"},
            {"id": "fable", "name": "Fable", "description": "A clear, expressive voice"},
            {"id": "onyx", "name": "Onyx", "description": "A deep, authoritative voice"},
            {"id": "nova", "name": "Nova", "description": "A bright, energetic voice"},
            {"id": "shimmer", "name": "Shimmer", "description": "A smooth, melodic voice"}
        ]


class GTTSProvider(TTSProvider):
    """Google Text-to-Speech provider using gTTS library."""
    
    def __init__(self):
        try:
            import gtts
            self.gtts = gtts
        except ImportError:
            raise ImportError("gTTS package not installed. Install with: pip install gTTS")
    
    async def generate_speech(
        self,
        script: str,
        output_path: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate speech using gTTS."""
        try:
            import asyncio
            import os
            
            # Prepare settings
            language = voice_settings.get("language", "en") if voice_settings else "en"
            slow = voice_settings.get("slow", False) if voice_settings else False
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            start_time = asyncio.get_event_loop().time()
            
            # Generate speech (run in thread since gTTS is blocking)
            def _generate():
                tts = self.gtts.gTTS(text=script, lang=language, slow=slow)
                tts.save(output_path)
            
            await asyncio.to_thread(_generate)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Get file size for basic metrics
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            logger.info(f"gTTS completed in {processing_time:.2f}s, file size: {file_size} bytes")
            
            return {
                "provider": "gtts",
                "output_path": output_path,
                "processing_time": processing_time,
                "language": language,
                "file_size": file_size,
                "duration_seconds": len(script.split()) / 150,  # Rough estimate: 150 WPM
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"gTTS failed: {e}")
            raise
    
    async def get_available_voices(self) -> list:
        """Get available languages from gTTS."""
        return [
            {"id": "en", "name": "English", "description": "English (US)"},
            {"id": "en-uk", "name": "English (UK)", "description": "English (United Kingdom)"},
            {"id": "es", "name": "Spanish", "description": "Spanish"},
            {"id": "fr", "name": "French", "description": "French"},
            {"id": "de", "name": "German", "description": "German"},
            {"id": "it", "name": "Italian", "description": "Italian"},
            {"id": "pt", "name": "Portuguese", "description": "Portuguese"},
            {"id": "ru", "name": "Russian", "description": "Russian"},
            {"id": "ja", "name": "Japanese", "description": "Japanese"},
            {"id": "ko", "name": "Korean", "description": "Korean"},
            {"id": "zh", "name": "Chinese", "description": "Chinese (Mandarin)"},
        ]


class TTSProviderFactory:
    """Factory for creating TTS provider instances."""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> TTSProvider:
        """Create a TTS provider instance."""
        provider_name = provider_name or settings.tts_provider
        
        try:
            if provider_name == "elevenlabs":
                if not settings.elevenlabs_api_key:
                    raise ValueError("ElevenLabs API key not configured")
                return ElevenLabsProvider()
            elif provider_name == "openai":
                if not settings.openai_api_key:
                    raise ValueError("OpenAI API key not configured")
                return OpenAITTSProvider()
            elif provider_name == "gtts":
                return GTTSProvider()
            else:
                # Try available providers in order of preference
                try:
                    return GTTSProvider()  # gTTS is free, try it first
                except ImportError:
                    pass
                
                if settings.elevenlabs_api_key:
                    return ElevenLabsProvider()
                elif settings.openai_api_key:
                    return OpenAITTSProvider()
                else:
                    raise ValueError("No TTS provider available")
                    
        except Exception as e:
            logger.error(f"Failed to create TTS provider '{provider_name}': {e}")
            raise 