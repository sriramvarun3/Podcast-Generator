"""
Web search service for finding diverse sources about podcast topics.
"""

import asyncio
import httpx
from typing import List, Dict, Any
from urllib.parse import urlparse
import re
from loguru import logger

from app.core.config import settings
from app.models.podcast import Source


class WebSearchService:
    """Service for searching the web for diverse sources."""
    
    def __init__(self):
        self.search_provider = settings.search_provider
        self.max_results = settings.max_search_results
        
    async def search_topic(self, topic: str, description: str = "") -> List[Source]:
        """
        Search for diverse sources about a given topic.
        
        Args:
            topic: Main topic to search for
            description: Additional context for the search
            
        Returns:
            List of relevant sources
        """
        logger.info(f"Searching for sources about topic: {topic}")
        
        # Combine topic and description for better search
        search_query = f"{topic} {description}".strip()
        
        try:
            if self.search_provider == "duckduckgo":
                sources = await self._search_duckduckgo(search_query)
            elif self.search_provider == "google":
                sources = await self._search_google(search_query)
            else:
                # Fallback to DuckDuckGo
                sources = await self._search_duckduckgo(search_query)
            
            # Filter and rank sources
            filtered_sources = self._filter_and_rank_sources(sources)
            
            logger.info(f"Found {len(filtered_sources)} relevant sources for topic: {topic}")
            return filtered_sources[:self.max_results]
            
        except Exception as e:
            logger.error(f"Error searching for topic '{topic}': {e}")
            return []
    
    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo Instant Answer API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                sources = []
                
                # Extract related topics
                if "RelatedTopics" in data:
                    for topic in data["RelatedTopics"]:
                        if "FirstURL" in topic and "Text" in topic:
                            sources.append({
                                "url": topic["FirstURL"],
                                "title": topic["Text"],
                                "snippet": topic.get("Text", "")
                            })
                
                # Extract abstract source
                if "AbstractURL" in data and data["AbstractURL"]:
                    sources.append({
                        "url": data["AbstractURL"],
                        "title": data.get("Abstract", "Source"),
                        "snippet": data.get("Abstract", "")
                    })
                
                return sources
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    async def _search_google(self, query: str) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API (requires API key)."""
        # This would require Google Custom Search API setup
        # For now, return empty list
        logger.warning("Google search not implemented - requires API key")
        return []
    
    def _filter_and_rank_sources(self, sources: List[Dict[str, Any]]) -> List[Source]:
        """Filter and rank sources by relevance and quality."""
        filtered_sources = []
        
        for source in sources:
            try:
                url = source.get("url", "")
                if not url or not self._is_valid_url(url):
                    continue
                
                # Extract domain
                domain = urlparse(url).netloc
                
                # Skip certain domains
                if self._should_skip_domain(domain):
                    continue
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(
                    source.get("title", ""),
                    source.get("snippet", ""),
                    domain
                )
                
                # Only include sources with decent relevance
                if relevance_score > 0.3:
                    filtered_sources.append(Source(
                        url=url,
                        title=source.get("title", "Untitled"),
                        domain=domain,
                        content_length=len(source.get("snippet", "")),
                        relevance_score=relevance_score
                    ))
                    
            except Exception as e:
                logger.warning(f"Error processing source {source}: {e}")
                continue
        
        # Sort by relevance score (descending)
        filtered_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return filtered_sources
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and accessible."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except:
            return False
    
    def _should_skip_domain(self, domain: str) -> bool:
        """Check if domain should be skipped."""
        skip_patterns = [
            r"facebook\.com",
            r"twitter\.com",
            r"instagram\.com",
            r"youtube\.com",
            r"reddit\.com",
            r"wikipedia\.org",  # Skip Wikipedia for diversity
            r"\.gov$",  # Skip government sites
            r"\.edu$",  # Skip educational institutions
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_relevance_score(self, title: str, snippet: str, domain: str) -> float:
        """Calculate relevance score for a source."""
        score = 0.0
        
        # Domain authority (simplified)
        if any(trusted in domain.lower() for trusted in ["reuters", "bbc", "cnn", "nytimes", "wsj"]):
            score += 0.2
        
        # Content length
        content_length = len(title) + len(snippet)
        if content_length > 100:
            score += 0.1
        
        # Title relevance (simplified keyword matching)
        title_lower = title.lower()
        if len(title_lower) > 10:
            score += 0.1
        
        # Normalize score
        return min(1.0, score)
    
    async def get_diverse_sources(self, topic: str, description: str = "") -> List[Source]:
        """
        Get diverse sources by searching multiple queries.
        
        Args:
            topic: Main topic
            description: Additional context
            
        Returns:
            List of diverse sources
        """
        # Generate multiple search queries for diversity
        search_queries = [
            f"{topic}",
            f"{topic} news",
            f"{topic} latest",
            f"{topic} analysis",
            f"{topic} expert opinion"
        ]
        
        if description:
            search_queries.append(f"{topic} {description}")
        
        # Search with all queries concurrently
        tasks = [self.search_topic(query) for query in search_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        all_sources = []
        seen_urls = set()
        
        for result in results:
            if isinstance(result, list):
                for source in result:
                    if source.url not in seen_urls:
                        all_sources.append(source)
                        seen_urls.add(source.url)
        
        # Sort by relevance and return top results
        all_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_sources[:self.max_results] 