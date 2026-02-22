import logging
import json
import networkx as nx
from typing import List, Dict, Any
from pydantic import BaseModel
from nexus_insight.cognition.state import RawSource
from nexus_insight.infra.llm_router import LLMRouter
from nexus_insight.infra.otel import trace_node

logger = logging.getLogger(__name__)

class GraphEdge(BaseModel):
    source_entity: str
    target_entity: str
    relationship: str
    context: str

class GraphExtractor:
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
        self.graph = nx.DiGraph()

    @trace_node("graph_extraction")
    async def extract_and_build(self, sources: List[RawSource], query: str) -> str:
        """
        Parses sources to extract entities and builds a NetworkX Knowledge Graph.
        Returns a text summary of the most central nodes and paths.
        """
        if not sources:
            return "No sources available for Graph Construction."

        llm = await self.llm_router.get_llm("fast")
        
        # Limit to top 3 sources to save tokens for fast extraction
        texts_to_process = [s.content[:1500] for s in sources[:3]]
        
        for idx, text in enumerate(texts_to_process):
            prompt = (
                f"You are a Knowledge Graph extraction engine.\n"
                f"Given the following text, extract 3 to 5 key entity relationships relevant to the query: '{query}'.\n\n"
                f"Text: {text}\n\n"
                f"Respond ONLY with a valid JSON array of objects in this exact format:\n"
                f"[{{\"source_entity\": \"EntityA\", \"target_entity\": \"EntityB\", \"relationship\": \"caused by\", \"context\": \"brief detail\"}}]"
            )
            
            try:
                response = await llm.ainvoke(prompt)
                data = json.loads(response.content)
                
                for rel in data:
                    src = rel.get("source_entity", "").strip().upper()
                    tgt = rel.get("target_entity", "").strip().upper()
                    if src and tgt:
                        self.graph.add_edge(
                            src, tgt, 
                            relationship=rel.get("relationship", "related"),
                            context=rel.get("context", "")
                        )
            except Exception as e:
                logger.warning(f"Failed to parse graph edges for source {idx}: {e}")
                continue

        if self.graph.number_of_nodes() == 0:
            return "Graph built, but no strong semantic connections were found."

        return self._summarize_graph()

    def _summarize_graph(self) -> str:
        """
        Analyzes the NetworkX graph using PageRank to find central themes.
        """
        try:
            # Calculate node importance
            centrality = nx.pagerank(self.graph)
            
            # Get top 5 most important entities
            top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            
            summary = "### Knowledge Graph Structural Analysis\n"
            summary += "**Central Entities (Hubs):**\n"
            for node, score in top_nodes:
                summary += f"- {node} (Centrality: {score:.2f})\n"
                
            summary += "\n**Key Semantic Pathways:**\n"
            edges = list(self.graph.edges(data=True))[:5] # Sample paths
            for u, v, data in edges:
                summary += f"- {u} --[{data['relationship']}]--> {v} ({data['context'][:50]}...)\n"
                
            return summary
            
        except Exception as e:
            logger.error(f"Graph analysis failed: {e}")
            return "Graph construction completed, but analysis failed."
