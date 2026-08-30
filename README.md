# AI Co-Founder

**Team:** QuadNova – University of Moratuwa  
**Project Type:** Agentic AI / Multi-Agent Startup Advisory System

AI Co-Founder is an autonomous multi-agent AI platform that acts as an on-demand virtual co-founder for aspiring entrepreneurs. It validates raw startup ideas, analyzes markets with live web research, builds business models using RAG, estimates deterministic revenues, and plans 90-day GTM roadmaps.

## 🏗️ Architecture Overview

- **Central Orchestrator (Member 1)**: LangGraph stateful graph with conditional routing, self-healing retries, checkpointing, and re-planning loops.
- **Idea Analysis & Business Model (Member 2)**: Problem clarification, assumptions, and RAG-driven startup framework canvas generation (BMC, Lean Canvas, SWOT, Porter's 5 Forces).
- **Market Research & Critic (Member 3)**: Live grounded web search, competitor analysis, TAM/SAM/SOM signals, and factual evidence validation.
- **Revenue Estimation & Financial Engine (Member 4)**: Structured parameter generation paired with a deterministic Python math engine ($SOM \le SAM \le TAM$, unit economics, sensitivity).
- **Marketing & Roadmap Viewer (Member 5)**: 90-day actionable GTM plan, Next.js frontend UI, and PDF/Word roadmap export.

## 🚀 Quick Start

### 1. Dev Hybrid Mode (Recommended for Development)
```bash
# Start PostgreSQL and Redis in Docker
docker compose up -d postgres redis

# Install shared contracts
pip install -e shared/

# Run backend orchestrator
cd services/orchestrator
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# In another terminal: Run frontend
cd ../../apps/frontend
npm install
npm run dev
```

### 2. Full Docker Mode
```bash
docker compose up --build
```
