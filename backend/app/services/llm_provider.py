"""
Pluggable LLM provider adapter for generating podcast scripts.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import asyncio
from loguru import logger

from app.core.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_script(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        extracted_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a podcast script from extracted content."""
        pass
    
    @abstractmethod
    async def generate_script_from_text(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_text: str
    ) -> Dict[str, Any]:
        """Generate a podcast script from raw text content (fallback mode)."""
        pass
    
    @abstractmethod
    async def summarize_content(
        self,
        content: List[Dict[str, Any]]
    ) -> str:
        """Summarize extracted content into key points."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self):
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
        except ImportError:
            raise ImportError("OpenAI package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    async def generate_script(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        extracted_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate podcast script using OpenAI."""
        try:
            # Prepare content summary
            content_summary = await self.summarize_content(extracted_content)
            
            # Create prompt for script generation
            prompt = self._create_script_prompt(
                topic, description, tone, target_length, content_summary
            )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert podcast script writer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            script = response.choices[0].message.content
            
            return {
                "script": script,
                "word_count": len(script.split()),
                "provider": "openai",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"OpenAI script generation failed: {e}")
            raise
    
    async def generate_script_from_text(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_text: str
    ) -> Dict[str, Any]:
        """Generate podcast script from raw text content (fallback mode)."""
        try:
            prompt = f"""
            Create an engaging podcast script about "{topic}" based on the following content.
            
            Topic: {topic}
            Description: {description}
            Tone: {tone}
            Target Length: {target_length} minutes
            
            Content to work with:
            {content_text}
            
            Please create a podcast script that:
            1. Is engaging and conversational in a {tone} tone
            2. Is approximately {target_length} minutes long when spoken
            3. Includes natural transitions and flow
            4. Has an engaging introduction and conclusion
            5. Incorporates the provided content naturally
            
            Format the script with clear paragraphs. Do not include speaker names or technical directions.
            Just write the content that should be spoken.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert podcast script writer who creates engaging, conversational content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            script = response.choices[0].message.content.strip()
            
            return {
                "script": script,
                "word_count": len(script.split()),
                "provider": "openai",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"OpenAI script generation from text failed: {e}")
            raise
    
    async def summarize_content(
        self,
        content: List[Dict[str, Any]]
    ) -> str:
        """Summarize extracted content using OpenAI."""
        try:
            # Prepare content for summarization
            content_text = "\n\n".join([
                f"Source: {item['source'].title}\nContent: {item['extracted_text'][:1000]}..."
                for item in content
            ])
            
            prompt = f"""Summarize the following content into key points for a podcast:

{content_text}

Provide a concise summary focusing on the most important and interesting information:"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert content summarizer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI content summarization failed: {e}")
            raise
    
    def _create_script_prompt(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_summary: str
    ) -> str:
        """Create a prompt for script generation."""
        return f"""Create a podcast script about "{topic}" with the following requirements:

Topic: {topic}
Description: {description}
Tone: {tone}
Target Length: {target_length} minutes

Content Summary:
{content_summary}

Instructions:
1. Write in a {tone} tone that matches the specified style
2. Structure the script for approximately {target_length} minutes of audio
3. Include an engaging introduction, main content sections, and conclusion
4. Use conversational language suitable for podcast delivery
5. Include natural transitions and engaging hooks
6. Make it informative and entertaining
7. Format with clear section breaks and speaker notes if needed

Generate a complete podcast script:"""


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self):
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = settings.anthropic_model
        except ImportError:
            raise ImportError("Anthropic package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise
    
    async def generate_script(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        extracted_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate podcast script using Anthropic Claude."""
        try:
            content_summary = await self.summarize_content(extracted_content)
            
            prompt = self._create_script_prompt(
                topic, description, tone, target_length, content_summary
            )
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            script = response.content[0].text
            
            return {
                "script": script,
                "word_count": len(script.split()),
                "provider": "anthropic",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Anthropic script generation failed: {e}")
            raise
    
    async def generate_script_from_text(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_text: str
    ) -> Dict[str, Any]:
        """Generate podcast script from raw text content (fallback mode)."""
        try:
            prompt = f"""
            Create an engaging podcast script about "{topic}" based on the following content.
            
            Topic: {topic}
            Description: {description}
            Tone: {tone}
            Target Length: {target_length} minutes
            
            Content to work with:
            {content_text}
            
            Please create a podcast script that:
            1. Is engaging and conversational in a {tone} tone
            2. Is approximately {target_length} minutes long when spoken
            3. Includes natural transitions and flow
            4. Has an engaging introduction and conclusion
            5. Incorporates the provided content naturally
            
            Format the script with clear paragraphs. Do not include speaker names or technical directions.
            Just write the content that should be spoken.
            """
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            script = response.content[0].text.strip()
            
            return {
                "script": script,
                "word_count": len(script.split()),
                "provider": "anthropic",
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Anthropic script generation from text failed: {e}")
            raise
    
    async def summarize_content(
        self,
        content: List[Dict[str, Any]]
    ) -> str:
        """Summarize extracted content using Anthropic Claude."""
        try:
            content_text = "\n\n".join([
                f"Source: {item['source'].title}\nContent: {item['extracted_text'][:1000]}..."
                for item in content
            ])
            
            prompt = f"""Summarize the following content into key points for a podcast:

{content_text}

Provide a concise summary focusing on the most important and interesting information:"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic content summarization failed: {e}")
            raise
    
    def _create_script_prompt(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_summary: str
    ) -> str:
        """Create a prompt for script generation."""
        return f"""Create a podcast script about "{topic}" with the following requirements:

Topic: {topic}
Description: {description}
Tone: {tone}
Target Length: {target_length} minutes

Content Summary:
{content_summary}

Instructions:
1. Write in a {tone} tone that matches the specified style
2. Structure the script for approximately {target_length} minutes of audio
3. Include an engaging introduction, main content sections, and conclusion
4. Use conversational language suitable for podcast delivery
5. Include natural transitions and engaging hooks
6. Make it informative and entertaining
7. Format with clear section breaks and speaker notes if needed

Generate a complete podcast script:"""


class GoogleAIProvider(LLMProvider):
    """Google AI Gemini provider implementation."""
    
    def __init__(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.google_model)
        except ImportError:
            raise ImportError("Google Generative AI package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Google AI client: {e}")
            raise
    
    async def generate_script(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        extracted_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate podcast script using Google AI Gemini."""
        try:
            content_summary = await self.summarize_content(extracted_content)
            
            prompt = self._create_script_prompt(
                topic, description, tone, target_length, content_summary
            )
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            script = response.text
            
            return {
                "script": script,
                "word_count": len(script.split()),
                "provider": "google_ai",
                "model": settings.google_model
            }
            
        except Exception as e:
            logger.error(f"Google AI script generation failed: {e}")
            raise
    
    async def generate_script_from_text(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_text: str
    ) -> Dict[str, Any]:
        """Generate podcast script from raw text content (fallback mode)."""
        try:
            prompt = f"""
            Create an engaging podcast script about "{topic}" based on the following content.
            
            Topic: {topic}
            Description: {description}
            Tone: {tone}
            Target Length: {target_length} minutes
            
            Content to work with:
            {content_text}
            
            Please create a podcast script that:
            1. Is engaging and conversational in a {tone} tone
            2. Is approximately {target_length} minutes long when spoken
            3. Includes natural transitions and flow
            4. Has an engaging introduction and conclusion
            5. Incorporates the provided content naturally
            
            Format the script with clear paragraphs. Do not include speaker names or technical directions.
            Just write the content that should be spoken.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            script = response.text.strip()
            
            return {
                "script": script,
                "word_count": len(script.split()),
                "provider": "google_ai",
                "model": settings.google_model
            }
            
        except Exception as e:
            logger.error(f"Google AI script generation from text failed: {e}")
            raise
    
    async def summarize_content(
        self,
        content: List[Dict[str, Any]]
    ) -> str:
        """Summarize extracted content using Google AI Gemini."""
        try:
            content_text = "\n\n".join([
                f"Source: {item['source'].title}\nContent: {item['extracted_text'][:1000]}..."
                for item in content
            ])
            
            prompt = f"""Summarize the following content into key points for a podcast:

{content_text}

Provide a concise summary focusing on the most important and interesting information:"""
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Google AI content summarization failed: {e}")
            raise
    
    def _create_script_prompt(
        self,
        topic: str,
        description: str,
        tone: str,
        target_length: int,
        content_summary: str
    ) -> str:
        """Create a prompt for script generation."""
        return f"""Create a podcast script about "{topic}" with the following requirements:

Topic: {topic}
Description: {description}
Tone: {tone}
Target Length: {target_length} minutes

Content Summary:
{content_summary}

Instructions:
1. Write in a {tone} tone that matches the specified style
2. Structure the script for approximately {target_length} minutes of audio
3. Include an engaging introduction, main content sections, and conclusion
4. Use conversational language suitable for podcast delivery
5. Include natural transitions and engaging hooks
6. Make it informative and entertaining
7. Format with clear section breaks and speaker notes if needed

Generate a complete podcast script:"""


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> LLMProvider:
        """Create an LLM provider instance."""
        provider_name = provider_name or settings.llm_provider
        
        try:
            if provider_name == "openai":
                if not settings.openai_api_key:
                    raise ValueError("OpenAI API key not configured")
                return OpenAIProvider()
            elif provider_name == "anthropic":
                if not settings.anthropic_api_key:
                    raise ValueError("Anthropic API key not configured")
                return AnthropicProvider()
            elif provider_name == "google_ai":
                if not settings.google_api_key:
                    raise ValueError("Google AI API key not configured")
                return GoogleAIProvider()
            else:
                # Try OpenAI as default
                if settings.openai_api_key:
                    return OpenAIProvider()
                elif settings.anthropic_api_key:
                    return AnthropicProvider()
                elif settings.google_api_key:
                    return GoogleAIProvider()
                else:
                    raise ValueError("No LLM provider configured")
                    
        except Exception as e:
            logger.error(f"Failed to create LLM provider '{provider_name}': {e}")
            raise 