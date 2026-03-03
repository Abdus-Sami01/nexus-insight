import logging
from typing import List, Dict, Any, Optional
import httpx
import xml.etree.ElementTree as ET
from nexus_insight.cognition.state import RawSource, SourceType

logger = logging.getLogger(__name__)

class PubmedTool:
    """
    Tool to search for and parse biomedical literature from PubMed (NCBI Entrez API).
    """
    
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    async def search(self, query: str, max_results: int = 3) -> List[RawSource]:
        """
        Search PubMed for relevant papers and return as RawSource objects.
        """
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Search for IDs
                search_res = await client.get(self.ESEARCH_URL, params=search_params)
                search_res.raise_for_status()
                id_list = search_res.json().get("esearchresult", {}).get("idlist", [])
                
                if not id_list:
                    return []
                
                # 2. Fetch summaries
                summary_params = {
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "json"
                }
                summary_res = await client.get(self.ESUMMARY_URL, params=summary_params)
                summary_res.raise_for_status()
                
                return self._parse_summaries(summary_res.json(), id_list)
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []

    def _parse_summaries(self, data: Dict[str, Any], id_list: List[str]) -> List[RawSource]:
        """
        Parse the PubMed summary JSON format.
        """
        sources = []
        result = data.get("result", {})
        
        for uid in id_list:
            paper = result.get(uid)
            if not paper:
                continue
                
            title = paper.get("title", "Unknown Title")
            # PubMed summaries don't contain full abstracts, usually just metadata.
            # We'll use the title and source as content if abstract isn't available.
            source = paper.get("source", "PubMed")
            pubdate = paper.get("pubdate", "")
            
            url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
            
            sources.append(RawSource(
                id=f"pubmed-{uid}",
                url=url,
                content=f"Title: {title}\nSource: {source}\nDate: {pubdate}",
                source_type=SourceType.WEB, # Treat as web since we don't have full PDF here usually
                trust_score=0.98, # PubMed is highly trusted
                metadata={
                    "title": title,
                    "engine": "pubmed",
                    "uid": uid,
                    "authors": [a.get("name") for a in paper.get("authors", [])]
                }
            ))
            
        return sources
