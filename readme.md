<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f0c29,50:302b63,100:24243e&height=200&section=header&text=Nexus-Insight&fontSize=72&fontColor=ffffff&fontAlignY=38&desc=Autonomous%20Multi-Modal%20Research%20%26%20Fact-Verification%20Agent&descAlignY=58&descSize=16&descColor=a78bfa" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-FF6B35?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Cost](https://img.shields.io/badge/API%20Cost-$0.00-gold?style=for-the-badge)](https://console.groq.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker-compose.yml)

<br/>

> **"Don't just search. Verify."** — Nexus-Insight is an autonomous research agent that reads the web, PDFs, and deep-dives into academic literature, then debates itself until the truth is cross-checked.

<br/>

<img src="https://raw.githubusercontent.com/Anmol-Baranwal/Cool-GIFs-For-GitHub/master/data/hyperkitty.gif" width="30px"/> &nbsp;
*Multi-agent. Self-correcting. Privacy-first. Fully free.*

</div>

---

## 💡 What is Nexus-Insight?

Nexus-Insight is a high-performance research powerhouse designed to combat AI hallucinations. Unlike simple RAG systems, it atomizes every claim into atomic facts and subjects them to a rigorous **4-phase Chain-of-Verification (CoV)**. 

### Why it stands out:
- **Academic Deep-Dives**: Native integration with **arXiv** and **PubMed** brings peer-reviewed reliability to your fingertips.
- **Interactive Knowledge Graphs**: Watch semantic maps of entities and relationships build in real-time, rendered interactively with Vis.js.
- **Adversarial Reasoning**: Two competing agents — a Proposer and a Skeptic — engage in structured debate to resolve contradictions and edge cases.
- **Privacy by Design**: Built-in **PII Redaction** anonymizes your queries locally before they ever touch a cloud API.
- **Zero-Cost Sovereignty**: Out-of-the-box support for **Groq**'s lightning-fast free tier and fully offline operation via **Ollama**.

---

## 🚀 Quickstart

### Get running in under 2 minutes:
```bash
# Clone and setup
git clone https://github.com/Abdus-Sami01/nexus-insight.git && cd nexus-insight
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Configure & Run
cp .env.example .env         # Add your FREE GROQ_API_KEY
docker-compose up redis searxng -d
python nexus_insight/main.py
```
*Access the dashboard at http://localhost:8080 to see the streaming thought-process and Knowledge Graph in action.*

---

## 🔬 How It Works

Nexus-Insight orchestrates a complex **11-node state machine** via LangGraph:

1.  **Intake & Redact**: Intent classification + local PII scrubbing.
2.  **Plan**: Task decomposition into modality-specific research queries.
3.  **Explore**: Parallel gathering across Web (SearXNG), PDF (Local FAISS), Media (Whisper), and Academic (arXiv/PubMed) channels.
4.  **Verify (CoV)**: Every claim is verified independently to eliminate anchoring bias.
5.  **Adversarial Debate**: Conflict resolution between competing AI personas.
6.  **Synthesize**: Citations-backed report generation with inline proof links.
7.  **Evaluate**: Sentenced-level faithfulness scoring to ensure total accuracy.

### 🛡️ Resilience & Efficiency
- **Circuit Breakers**: Fault-tolerant nodes that handle API timeouts gracefully.
- **Token Budgeting**: Active tracking of token consumption to manage limits and prevent reasoning loops.
- **LLM Routing**: Smart switching between cloud (Groq) and local (Ollama) backends.

---

## 🗺️ Roadmap Status

- [x] **LangGraph Orchestration**: Precise 11-node reasoning pipeline.
- [x] **Chain-of-Verification**: 4-phase "anti-hallucination" loop.
- [x] **Adversarial Debate**: Proposer vs. Skeptic consensus engine.
- [x] **Academic Mastery**: Direct **arXiv** & **PubMed** integration.
- [x] **Graph View**: Real-time Knowledge Graph visualization (Vis.js).
- [x] **Privacy Guard**: Native PII redaction & local embedding search.
- [x] **Token Budgeting**: Strict execution limits & cost tracking.
- [ ] **Multi-language**: Deep support for non-English sources.
- [ ] **News Feed Mode**: Continuous monitoring for breaking real-world events.

---

## 🤝 Contributing

We love builders! If you're adding new tools or refining prompts, please ensure `pytest tests/` passes and follow our `ruff` linting standards before submitting a PR.

---

## 📄 License
MIT License. High-fidelity research for everyone.

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:24243e,50:302b63,100:0f0c29&height=120&section=footer" width="100%"/>

*Star the project ⭐ if it helps your research workflow!*
</div>
