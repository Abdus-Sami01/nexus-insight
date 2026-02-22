# Nexus-Insight: Setup Guide

Welcome to Nexus-Insight, your autonomous research agent. This system is designed to be **100% free** and performance-optimized.

---

## PATH A: Groq Only (Fastest Setup)
*Ideal if you have a Groq API key and want minimal local dependencies.*

1. **Install Python Deps**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment Setup**:
   - Register at [console.groq.com](https://console.groq.com) (Free).
   - Copy `.env.example` to `.env` and add your `GROQ_API_KEY`.
   - Set `LLM_MODE=groq`.
3. **Start Storage/Search Services**:
   ```bash
   docker-compose up redis searxng otel-collector
   ```
4. **Initialize NLP Model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```
5. **Run Application**:
   ```bash
   python nexus_insight/main.py
   ```

---

## PATH B: Ollama Only (Fully Offline)
*Ideal for privacy and offline usage. Requires significant local RAM (16GB+).*

1. **Setup Ollama**:
   ```bash
   chmod +x setup_ollama.sh
   ./setup_ollama.sh
   ```
2. **Environment Setup**:
   - Set `LLM_MODE=ollama` in your `.env`.
3. **Run Application**:
   (Same as Path A, but Groq key is not required).

---

## PATH C: Full Docker (Production Grade)
*The recommended way to run everything in a containerized environment.*

1. **Environment Setup**:
   - Fill in your `.env` as per Path A or B.
2. **Launch Stack**:
   ```bash
   docker-compose up --build
   ```

---

## Simple Verification
Test the health endpoint:
```bash
curl http://localhost:8080/v1/health
```

Start a research quest:
```bash
curl -X POST http://localhost:8080/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare Llama 3.1 70B with GPT-4o on reasoning benchmarks.", "modalities": ["web"]}'
```
