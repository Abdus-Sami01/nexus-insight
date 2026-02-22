import asyncio
import logging
import httpx
from datetime import datetime
from typing import List, Optional, Dict
from duckduckgo_search import DDGS
from trafilatura import extract
from nexus_insight.cognition.state import RawSource, SourceType
from nexus_insight.config import settings
from nexus_insight.infra.resilience import exponential_backoff

logger = logging.getLogger(__name__)

class WebSearchTool:
    """
    Web search tool using DuckDuckGo as primary and SearXNG as fallback.
    No paid APIs required.
    """

    def __init__(self):
        pass  # No shared session — each search creates its own

    @exponential_backoff(max_retries=3, base_delay=settings.DDG_RATE_LIMIT_DELAY)
    async def search(self, query: str, max_results: int = 7) -> List[RawSource]:
        results = []
        try:
            logger.info(f"Searching DuckDuckGo for: {query}")
            # Fresh session per call avoids "Exception occurred in previous call"
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results, backend="lite"))
            for res in ddg_results:
                results.append({
                    "url": res["href"],
                    "title": res["title"],
                    "snippet": res["body"]
                })
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}. Trying SearXNG...")
            results = await self._searxng_fallback(query, max_results)

        if len(results) < 3:
            logger.info("Few results from DDG. Supplementing with SearXNG...")
            searx_results = await self._searxng_fallback(query, max_results)
            # Deduplicate by URL
            seen_urls = {res["url"] for res in results}
            for res in searx_results:
                if res["url"] not in seen_urls:
                    results.append(res)
                    seen_urls.add(res["url"])

        # Fetch contents in parallel
        sources = await asyncio.gather(*[self._fetch_content(res) for res in results[:max_results]])
        return [s for s in sources if s is not None]

    async def _searxng_fallback(self, query: str, max_results: int) -> List[Dict]:
        """Secondary search via self-hosted SearXNG"""
        try:
            async with httpx.AsyncClient() as client:
                params = {"q": query, "format": "json", "language": "en"}
                response = await client.get(f"{settings.SEARXNG_URL}/search", params=params, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return [{"url": r["url"], "title": r["title"], "snippet": r.get("content", "")} 
                            for r in data.get("results", [])[:max_results]]
        except Exception as e:
            logger.error(f"SearXNG fallback failed: {e}")
        return []

    async def _fetch_content(self, search_res: Dict) -> Optional[RawSource]:
        url = search_res["url"]
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=settings.TIMEOUT_WEB)
                if response.status_code != 200:
                    return None
                
                content = extract(response.text)
                if not content or len(content) < 200:
                    return None

                return RawSource(
                    id=f"web-{hash(url)}",
                    source_type=SourceType.WEB,
                    url=url,
                    content=content,
                    metadata={
                        "title": search_res["title"],
                        "snippet": search_res["snippet"]
                    },
                    trust_score=self._calculate_trust_score(url),
                    fetched_at=datetime.now()
                )
        except Exception as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return None

    def _calculate_trust_score(self, url: str) -> float:
        """Domain trust heuristics"""
        trust_map = {
            ".gov": 0.95, ".edu": 0.90, ".ac.uk": 0.90,
            "arxiv.org": 0.90, "pubmed.ncbi": 0.95,
            "wikipedia.org": 0.75, "github.com": 0.70,
            "bbc.com": 0.80, "reuters.com": 0.80
        }
        score = 0.50
        for domain, s in trust_map.items():
            if domain in url:
                score = max(score, s)
        
        # Blacklist check
        if any(bad in url for bad in ["ads.", "tracker.", "sponsored"]):
            score = 0.10
            
        return score
