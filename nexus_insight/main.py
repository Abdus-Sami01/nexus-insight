import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from nexus_insight.api.routes import router, set_orchestrator
from nexus_insight.agents.orchestrator import Orchestrator
from nexus_insight.agents.researcher import ResearcherAgent
from nexus_insight.agents.verifier import ChainOfVerificationVerifier
from nexus_insight.agents.debater import MultiAgentDebater
from nexus_insight.evaluation.faithfulness import FaithfulnessEvaluator
from nexus_insight.tools.web_search import WebSearchTool
from nexus_insight.tools.pdf_engine import PDFEngine
from nexus_insight.tools.media_analyzer import MediaAnalyzer
from nexus_insight.cognition.graph import GraphExtractor
from nexus_insight.cognition.embeddings import LocalEmbedder
from nexus_insight.infra.llm_router import LLMRouter
from nexus_insight.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Nexus-Insight",
        description="Autonomous Multi-modal Research Agent",
        version="2.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize components
    llm_router = LLMRouter()
    embedder = LocalEmbedder()
    
    web_tool = WebSearchTool()
    pdf_tool = PDFEngine(embedder)
    media_tool = MediaAnalyzer()
    
    researcher = ResearcherAgent(web_tool, pdf_tool, media_tool)
    verifier = ChainOfVerificationVerifier(llm_router)
    debater = MultiAgentDebater(llm_router)
    graph_extractor = GraphExtractor(llm_router)
    evaluator = FaithfulnessEvaluator(llm_router)
    
    orchestrator = Orchestrator(llm_router, researcher, verifier, debater, graph_extractor, evaluator)
    
    # Inject orchestrator into routes
    set_orchestrator(orchestrator)
    
    app.include_router(router)

    # Serve the web UI
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        return FileResponse(static_dir / "index.html")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Nexus-Insight Service Starting...")
        # Proactively check backends
        info = await llm_router.get_backend_info()
        logger.info(f"Backend Status: {info}")

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
