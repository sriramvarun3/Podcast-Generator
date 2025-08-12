"""
Content extraction service for scraping and cleaning web pages.
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import trafilatura
from readability import Document
from bs4 import BeautifulSoup
import re
from loguru import logger

from app.core.config import settings
from app.models.podcast import Source


class ContentExtractor:
    """Service for extracting clean text content from web pages."""
    
    def __init__(self):
        self.max_content_length = settings.max_content_length
        self.timeout = 30.0
        
    async def extract_content_from_sources(self, sources: List[Source]) -> List[Dict[str, Any]]:
        """
        Extract content from multiple sources concurrently.
        
        Args:
            sources: List of sources to extract content from
            
        Returns:
            List of extracted content with metadata
        """
        logger.info(f"Extracting content from {len(sources)} sources")
        
        # Extract content concurrently
        tasks = [self._extract_single_source(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        extracted_content = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to extract content from {sources[i].url}: {result}")
                continue
            
            if result:
                extracted_content.append(result)
        
        logger.info(f"Successfully extracted content from {len(extracted_content)} sources")
        return extracted_content
    
    async def _extract_single_source(self, source: Source) -> Optional[Dict[str, Any]]:
        """
        Extract content from a single source.
        
        Args:
            source: Source to extract content from
            
        Returns:
            Extracted content with metadata
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    str(source.url),
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                )
                response.raise_for_status()
                
                html_content = response.text
                content_type = response.headers.get("content-type", "")
                
                # Extract content using multiple methods
                extracted_text = await self._extract_text(html_content, content_type)
                
                if not extracted_text or len(extracted_text.strip()) < 100:
                    logger.warning(f"Extracted content too short for {source.url}")
                    return None
                
                # Clean and process the text
                cleaned_text = self._clean_text(extracted_text)
                
                # Truncate if too long
                if len(cleaned_text) > self.max_content_length:
                    cleaned_text = cleaned_text[:self.max_content_length] + "..."
                
                return {
                    "source": source,
                    "raw_html": html_content,
                    "extracted_text": cleaned_text,
                    "word_count": len(cleaned_text.split()),
                    "extraction_method": "trafilatura",  # or readability
                    "content_type": content_type,
                    "status": "success"
                }
                
        except Exception as e:
            logger.error(f"Error extracting content from {source.url}: {e}")
            return None
    
    async def _extract_text(self, html_content: str, content_type: str) -> str:
        """
        Extract text content from HTML using multiple methods.
        
        Args:
            html_content: Raw HTML content
            content_type: Content type header
            
        Returns:
            Extracted text content
        """
        # Try trafilatura first (better for news/articles)
        try:
            extracted = trafilatura.extract(
                html_content,
                include_formatting=False,
                include_links=False,
                include_images=False,
                include_tables=False
            )
            if extracted and len(extracted.strip()) > 200:
                return extracted
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed: {e}")
        
        # Fallback to readability-lxml
        try:
            doc = Document(html_content)
            extracted = doc.summary()
            if extracted:
                # Convert HTML to text
                soup = BeautifulSoup(extracted, "html.parser")
                return soup.get_text(separator=" ", strip=True)
        except Exception as e:
            logger.debug(f"Readability extraction failed: {e}")
        
        # Last resort: basic BeautifulSoup extraction
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Get text from body or main content areas
            content_areas = soup.find_all(["article", "main", "div"], class_=re.compile(r"content|article|post|entry", re.I))
            
            if content_areas:
                text = " ".join([area.get_text(separator=" ", strip=True) for area in content_areas])
            else:
                text = soup.get_text(separator=" ", strip=True)
            
            return text
            
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed: {e}")
        
        return ""
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common web artifacts
        text = re.sub(r'Share this|Tweet this|Like this|Follow us|Subscribe|Newsletter', '', text, flags=re.IGNORECASE)
        
        # Remove social media buttons
        text = re.sub(r'Facebook|Twitter|Instagram|LinkedIn|YouTube', '', text, flags=re.IGNORECASE)
        
        # Remove common web elements
        text = re.sub(r'Cookie Policy|Privacy Policy|Terms of Service|Contact Us|About Us', '', text, flags=re.IGNORECASE)
        
        # Remove excessive punctuation
        text = re.sub(r'[.!?]{3,}', '...', text)
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _extract_metadata(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extract metadata from HTML content.
        
        Args:
            html_content: Raw HTML content
            url: Source URL
            
        Returns:
            Extracted metadata
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            metadata = {
                "title": "",
                "description": "",
                "author": "",
                "published_date": "",
                "keywords": [],
                "language": "en"
            }
            
            # Extract title
            title_tag = soup.find("title")
            if title_tag:
                metadata["title"] = title_tag.get_text(strip=True)
            
            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                metadata["description"] = meta_desc.get("content", "")
            
            # Extract author
            author_meta = soup.find("meta", attrs={"name": "author"})
            if author_meta:
                metadata["author"] = author_meta.get("content", "")
            
            # Extract published date
            date_meta = soup.find("meta", attrs={"property": "article:published_time"})
            if date_meta:
                metadata["published_date"] = date_meta.get("content", "")
            
            # Extract keywords
            keywords_meta = soup.find("meta", attrs={"name": "keywords"})
            if keywords_meta:
                keywords = keywords_meta.get("content", "")
                metadata["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]
            
            # Extract language
            lang_attr = soup.find("html", attrs={"lang": True})
            if lang_attr:
                metadata["language"] = lang_attr.get("lang", "en")
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Metadata extraction failed: {e}")
            return {
                "title": "",
                "description": "",
                "author": "",
                "published_date": "",
                "keywords": [],
                "language": "en"
            }
    
    async def validate_source_accessibility(self, sources: List[Source]) -> List[Source]:
        """
        Validate that sources are accessible and extractable.
        
        Args:
            sources: List of sources to validate
            
        Returns:
            List of accessible sources
        """
        logger.info(f"Validating accessibility of {len(sources)} sources")
        
        accessible_sources = []
        
        for source in sources:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.head(str(source.url))
                    if response.status_code == 200:
                        accessible_sources.append(source)
                    else:
                        logger.warning(f"Source {source.url} returned status {response.status_code}")
                        
            except Exception as e:
                logger.warning(f"Source {source.url} is not accessible: {e}")
                continue
        
        logger.info(f"Found {len(accessible_sources)} accessible sources")
        return accessible_sources 