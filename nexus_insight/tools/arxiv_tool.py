import logging
from typing import List, Dict, Any, Optional
import httpx
import xml.etree.ElementTree as ET
from nexus_insight.cognition.state import RawSource, SourceType

logger = logging.getLogger(__name__)

class ArxivTool:
    """
    Tool to search for and parse academic papers from arXiv API.
    """
    
    BASE_URL = "http://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 3) -> List[RawSource]:
        """
        Search arXiv for relevant papers and return as RawSource objects.
        """
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
                return self._parse_atom_feed(response.text)
        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            return []

    def _parse_atom_feed(self, xml_content: str) -> List[RawSource]:
        """
        Parse the arXiv Atom feed XML format.
        """
        sources = []
        try:
            root = ET.fromstring(xml_content)
            # Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip()
                summary = entry.find('atom:summary', ns).text.strip()
                id_url = entry.find('atom:id', ns).text.strip()
                
                # Try to find the PDF link
                url = id_url
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf' or link.get('type') == 'application/pdf':
                        url = link.get('href')
                        break
                
                # Check for PDF link transformation (abs/id to pdf/id)
                if "/abs/" in url:
                    url = url.replace("/abs/", "/pdf/")
                if not url.endswith(".pdf") and "/pdf/" in url:
                    url = url + ".pdf"

                sources.append(RawSource(
                    id=f"arxiv-{len(sources)}",
                    url=url,
                    content=summary,
                    source_type=SourceType.PDF, # Treat as PDF for downstream processing
                    trust_score=0.95, # Academic sources have high trust
                    metadata={
                        "title": title,
                        "engine": "arxiv",
                        "abstract": summary
                    }
                ))
            return sources
        except Exception as e:
            logger.error(f"Error parsing arXiv XML: {e}")
            return []
