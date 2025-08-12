"""
Configuration settings for the podcast generator application.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Podcast Generator API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=False, env="RELOAD")
    
    # CORS
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    
    # Static files
    static_dir: str = "static"
    upload_dir: str = "uploads"
    
    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(default=None, env="ELEVENLABS_API_KEY")
    
    # Model settings
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")
    google_model: str = Field(default="gemini-1.5-flash", env="GOOGLE_MODEL")
    
    # Provider settings
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")
    tts_provider: str = Field(default="gtts", env="TTS_PROVIDER")
    search_provider: str = Field(default="duckduckgo", env="SEARCH_PROVIDER")
    
    # Web search settings
    max_search_results: int = Field(default=10, env="MAX_SEARCH_RESULTS")
    search_timeout: int = Field(default=30, env="SEARCH_TIMEOUT")
    
    # Content extraction settings
    max_content_length: int = Field(default=5000, env="MAX_CONTENT_LENGTH")
    extraction_timeout: int = Field(default=60, env="EXTRACTION_TIMEOUT")
    
    # Audio settings
    target_lufs: float = Field(default=-16.0, env="TARGET_LUFS")
    sample_rate: int = Field(default=44100, env="SAMPLE_RATE")
    bit_rate: int = Field(default=192, env="BIT_RATE")
    
    # Job queue settings
    job_cleanup_interval: int = Field(default=3600, env="JOB_CLEANUP_INTERVAL")  # 1 hour
    
    # File cleanup settings
    max_file_age_hours: int = Field(default=24, env="MAX_FILE_AGE_HOURS")
    
    # Rate limiting
    max_requests_per_minute: int = Field(default=60, env="MAX_REQUESTS_PER_MINUTE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 