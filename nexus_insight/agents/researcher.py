import logging
import asyncio
from typing import List, Dict, Any
from nexus_insight.cognition.state import RawSource, ResearchState
from nexus_insight.tools.web_search import WebSearchTool
from nexus_insight.tools.pdf_engine import PDFEngine
from nexus_insight.tools.media_analyzer import MediaAnalyzer

logger = logging.getLogger(__name__)

class ResearcherAgent:
    """
    Async tool-use agent that executes research tasks across modalities.
    """

    def __init__(
        self, 
        web_tool: WebSearchTool, 
        pdf_tool: PDFEngine, 
        media_tool: MediaAnalyzer
    ):
        self.web_tool = web_tool
        self.pdf_tool = pdf_tool
        self.media_tool = media_tool

    async def explore(self, queries: List[str], modalities: List[str], pdf_urls: List[str] = None, video_urls: List[str] = None) -> List[RawSource]:
        """
        Parallel async execution of research tools.
        """
        tasks = []

        # 1. Web Search
        if "web" in modalities:
            for q in queries:
                tasks.append(self.web_tool.search(q))

        # 2. PDF Processing
        if "pdf" in modalities and pdf_urls:
            for url in pdf_urls:
                tasks.append(self.pdf_tool.process_source(url))

        # 3. Media Processing
        if "video" in modalities and video_urls:
            for url in video_urls:
                tasks.append(self.media_tool.process_video(url))

        logger.info(f"Launching {len(tasks)} research tasks across {modalities}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_sources = []
        for res in results:
            if isinstance(res, list):
                all_sources.extend(res)
            elif isinstance(res, RawSource):
                all_sources.append(res)
            elif isinstance(res, Exception):
                logger.error(f"Tool execution failed: {res}")
        
        return all_sources
