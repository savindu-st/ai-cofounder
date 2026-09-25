# AI Co-Founder Platform — Master Project Backlog & Implementation To-Do List

> **Project:** AI Co-Founder: Autonomous Multi-Agent Venture Creation Platform  
> **Team:** QuadNova — University of Moratuwa  
> **Status:** Active Implementation Phase  
> **Architecture Reference:** [`docs/architecture.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/architecture.md)  
> **Target Topology:** Monolithic LangGraph Engine (In-Process Domain Modules)  
> **Last Updated:** September 2026

---

## 📊 High-Level Implementation Status Overview

```
+------------------------------------+-----------------------+------------+
| Subsystem / Domain Module          | Owner                 | Status     |
+------------------------------------+-----------------------+------------+
| 1. Central Orchestrator & Graph    | Member 1 (Lead/Infra) | 🟡 SKELETON|
| 2. Business Intelligence & RAG     | Member 2              | 🟡 SKELETON|
| 3. Market Research & Critic Agent  | Member 3              | 🟡 SKELETON|
| 4. Deterministic Financial Engine  | Member 4              | 🟡 PARTIAL |
| 5. Marketing & Export Generators   | Member 5              | 🟢 ADVANCED|
| 6. Database & Persistence Tier     | Shared (Member 1 Lead)| 🔴 STUBBED |
| 7. Frontend Client (Next.js 14)    | Shared (Member 5 Lead)| 🟡 PARTIAL |
| 8. Evaluation Harness & Metrics    | Shared (Member 3 Lead)| 🔴 STUBBED |
| 9. Test Suite (Contract, Int, E2E) | Shared (Member 4 Lead)| 🔴 STUBBED |
| 10. Documentation & Demo Scenarios | All Members           | 🟡 PARTIAL |
+------------------------------------+-----------------------+------------+
```

---

## 🚨 Phase 0: Immediate Blockers & Repository Hygiene (P0 - Day 1)

These issues currently impede imports, clean builds, and test runs.

- [ ] **0.1 Fix Python Module Directory Names & Git Tracking**
  - **Issue:** Hyphenated folder names (`services/business-intelligence`, `services/marketing-output`) prevent clean Python imports. They have been renamed locally to snake_case (`services/business_intelligence`, `services/marketing_output`), but git has unstaged renames/deletions.
  - **Task:** Commit directory rename in git cleanly (`git add -A` and record clean file moves).
  - **Files:** [`services/business_intelligence/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence), [`services/marketing_output/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output).
- [ ] **0.2 Fix Pytest Module Collection Error**
  - **Issue:** Running `pytest` across all services fails with `ModuleNotFoundError: No module named 'tests.test_marketing_agent'`.
  - **Task:** Fix module path resolution in [`pyproject.toml`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/pyproject.toml) and ensure each `tests/` directory has proper namespace packaging.
  - **Acceptance Criteria:** `pytest` discovers and runs all tests without import crashes.
- [ ] **0.3 Update `docker-compose.yml` Service Paths**
  - **Task:** Ensure [`docker-compose.yml`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docker-compose.yml) build contexts and volume mounts reflect snake_case directories (`services/business_intelligence`, `services/marketing_output`).
- [ ] **0.4 Recreate Contract Tests**
  - **Issue:** `tests/contracts/__pycache__/` exists, but [`tests/contracts/test_contracts.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/tests/contracts) source file was removed.
  - **Task:** Implement automated Pydantic v2 schema validation tests for all shared contracts.

---

## 👤 Member 1: Orchestrator, LangGraph State Machine, API & Persistence

**Domain Lead:** Member 1  
**Primary Directory:** [`services/orchestrator/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator)  
**Shared Dependencies:** [`shared/contracts/venture_state.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/venture_state.py), [`database/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database)

### 1. LangGraph State Machine Core
- [ ] **1.1 Build LangGraph StateGraph Definition**
  - **File:** [`services/orchestrator/app/graph/workflow.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/graph/workflow.py)
  - **Task:** Implement `build_venture_workflow() -> CompiledGraph` using LangGraph `StateGraph(VentureState)`.
  - **Requirements:**
    - Register all 7 nodes: `idea_analysis`, `market_research`, `critic_validation`, `business_model`, `revenue_estimation`, `marketing_plan`, `roadmap_synthesis`.
    - Register `human_review_node` (pause interrupt node).
    - Attach checkpointer (`MemorySaver` for dev, `PostgresSaver` for production).
- [ ] **1.2 Implement Graph Node Execution Functions**
  - **File:** [`services/orchestrator/app/graph/nodes.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/graph/nodes.py)
  - **Task:** Implement async node wrappers calling domain interfaces:
    - `idea_analysis_node(state)` $\rightarrow$ calls `services.business_intelligence.app.interface:run_idea_analysis`
    - `market_research_node(state)` $\rightarrow$ calls `services.research.app.interface:run_market_research`
    - `critic_validation_node(state)` $\rightarrow$ calls `services.research.app.interface:run_critic_validation`
    - `business_model_node(state)` $\rightarrow$ calls `services.business_intelligence.app.interface:run_business_model`
    - `revenue_estimation_node(state)` $\rightarrow$ calls `services.finance.app.interface:run_revenue_estimation`
    - `marketing_plan_node(state)` $\rightarrow$ calls `services.marketing_output.app.interface:run_marketing_plan`
    - `roadmap_synthesis_node(state)` $\rightarrow$ calls `services.marketing_output.app.interface:run_roadmap_synthesis`
  - **Requirements:** Update `current_stage`, increment stage-specific timers, publish real-time SSE progress events to Redis on node enter/exit.
- [ ] **1.3 Implement Conditional Edge Routing Logic**
  - **Files:** [`services/orchestrator/app/graph/routing.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/graph/routing.py), [`services/orchestrator/app/graph/edges.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/graph/edges.py)
  - **Task:** Implement branching functions:
    - `route_after_critic(state)`:
      - If `market_validation.status == VALID` $\rightarrow$ proceed to `business_model`.
      - If total replans $> 5$ $\rightarrow$ route to `human_review_node`.
      - If `requires_pivot == True` or `REANALYSIS_REQUIRED` $\rightarrow$ route to `idea_analysis` (increment `replan_count`).
      - If `RESEARCH_REQUIRED` $\rightarrow$ route to `market_research` (increment `market_replan_count`, `replan_count`).
    - `route_after_revenue(state)`:
      - If `revenue_estimation.tam_sam_som_valid == True` and unit economics valid $\rightarrow$ proceed to `marketing_plan`.
      - If violations exist and `finance_retune_count < 2` $\rightarrow$ route to `revenue_estimation` internal retune (Tier 1).
      - If retune count $\ge 2$ and `replan_count <= 5` $\rightarrow$ route back to `market_research` with critique notes (Tier 2).
      - If total replans $> 5$ $\rightarrow$ route to `human_review_node`.
    - `route_after_human_review(state)`:
      - Resume based on founder's chosen action (`PROCEED_ANYWAY`, `OVERRIDE_ASSUMPTIONS`, or `ABORT`).

### 2. Orchestration, Resilience & Fault Tolerance
- [ ] **1.4 Implement Workflow Coordinator & Background Runner**
  - **File:** [`services/orchestrator/app/orchestration/coordinator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/orchestration/coordinator.py)
  - **Task:** Create background task runner managing graph invocation (`asyncio.create_task` or Celery/background workers), passing thread config `{"configurable": {"thread_id": venture_id}}`.
- [ ] **1.5 Implement Self-Healing Retry Handler with Provider Fallback**
  - **File:** [`services/orchestrator/app/orchestration/retry_handler.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/orchestration/retry_handler.py)
  - **Task:** Exponential backoff with jitter ($t = 2^r + \text{uniform}(0,1)$); multi-provider fallback chain (OpenAI $\rightarrow$ Anthropic $\rightarrow$ Google Gemini).
- [ ] **1.6 Implement Anti-Oscillation Critique History & Re-planning Logic**
  - **File:** [`services/orchestrator/app/orchestration/replanning.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/orchestration/replanning.py)
  - **Task:** Track critique history, prevent repetitive prompt cycles, construct critique context strings for downstream prompts.
- [ ] **1.7 Implement Exception Sandboxing & Crash Recovery**
  - **File:** [`services/orchestrator/app/orchestration/failure_handler.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/orchestration/failure_handler.py)
  - **Task:** Node timeout wrapper (`asyncio.wait_for(timeout=120s)`); on server startup, query non-terminal ventures in PostgreSQL and resume from last checkpoint.
- [ ] **1.8 Implement Human-in-the-Loop Interrupt & Resume Handler**
  - **File:** [`services/orchestrator/app/orchestration/human_review.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/orchestration/human_review.py)
  - **Task:** Manage pause state, handle resume actions (`PROCEED_ANYWAY`, `OVERRIDE_ASSUMPTIONS`, `ABORT`), update thread state in LangGraph.

### 3. API Gateway, Real-Time Streaming & State Hydration
- [ ] **1.9 Connect REST API to LangGraph Pipeline**
  - **File:** [`services/orchestrator/app/api/routes.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/api/routes.py)
  - **Task:** Update `POST /api/ventures/start` to trigger real background LangGraph execution and persist initial state to PostgreSQL.
  - **Task:** Update `GET /api/ventures/{venture_id}` to hydrate state directly from PostgreSQL / LangGraph checkpointer.
  - **Task:** Update `POST /api/ventures/{venture_id}/review` to unpause the LangGraph thread using `graph.update_state()` and resume execution.
- [ ] **1.10 Implement Real Redis Pub/Sub Event Streaming**
  - **File:** [`services/orchestrator/app/api/stream.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/api/stream.py)
  - **Task:** Replace simulated sleep generator with genuine Redis subscriber listening on `venture:{id}:events`. Emit standardized SSE payloads (`STAGE_STARTED`, `STAGE_PROGRESS`, `STAGE_COMPLETED`, `REPLAN_TRIGGERED`, `WARNING`, `HITL_REQUIRED`, `ROADMAP_READY`).

### 4. Database & State Persistence Implementation
- [ ] **1.11 Implement SQLAlchemy Database Models**
  - **Directory:** [`database/models/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models)
  - **Files:**
    - [`database/models/venture.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models/venture.py): Table `ventures` (id, user_id, title, status, created_at, updated_at).
    - [`database/models/venture_state.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models/venture_state.py): Table `venture_states` (venture_id, stage, state_json, updated_at).
    - [`database/models/agent_run.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models/agent_run.py): Table `agent_runs` (id, venture_id, node_name, duration_ms, tokens, cost, status).
    - [`database/models/evidence.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models/evidence.py): Table `evidence` (id, venture_id, claim, source_url, confidence_score).
    - [`database/models/roadmap.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models/roadmap.py): Table `roadmaps` (venture_id, roadmap_json, confidence_score, created_at).
    - [`database/models/user.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/database/models/user.py): Table `users` (id, email, hashed_password, created_at).
- [ ] **1.12 Implement Checkpointing & State Repository**
  - **Files:** [`services/orchestrator/app/state/checkpoint.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/state/checkpoint.py), [`services/orchestrator/app/state/state_manager.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/state/state_manager.py)
  - **Task:** Save full `VentureState` JSON at each stage boundary to `venture_states`; implement database transaction commits.

---

## 👤 Member 2: Business Intelligence, Idea Analysis & RAG BMC Agent

**Domain Lead:** Member 2  
**Primary Directory:** [`services/business_intelligence/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence)  
**Shared Dependencies:** [`shared/contracts/idea.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/idea.py), [`shared/contracts/business_model.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/business_model.py)

### 1. Idea Analysis Agent
- [ ] **2.1 Implement Idea Analysis LLM Agent**
  - **File:** [`services/business_intelligence/app/agents/idea_analysis/agent.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/agents/idea_analysis/agent.py)
  - **Task:** Build agent that deconstructs raw founder inputs into structured assumptions, customer segments, value propositions, and unfair advantages.
  - **Acceptance Criteria:** Returns valid [`IdeaAnalysisOutput`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/idea.py) conforming to Pydantic contract.
- [ ] **2.2 Implement Idea Analysis Prompt Templates & Schemas**
  - **Files:** [`services/business_intelligence/app/agents/idea_analysis/prompts.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/agents/idea_analysis/prompts.py), [`schemas.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/agents/idea_analysis/schemas.py)
  - **Task:** Prompts enforcing structured JSON schema output, extract problem statement, unfair advantages, primary audience personas, and testable hypotheses.
- [ ] **2.3 Implement Idea Validation & Sanitization**
  - **File:** [`services/business_intelligence/app/agents/idea_analysis/validator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/agents/idea_analysis/validator.py)
  - **Task:** Validate founder inputs (min length, non-empty problem description, reasonable industry categorizations). Flag ambiguous or unviable inputs early.

### 2. RAG Knowledge Base & Seeding Pipeline
- [ ] **2.4 Complete Startup Framework Knowledge Corpus**
  - **Directory:** [`services/business_intelligence/data/seed/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/data/seed)
  - **Files to complete/expand:**
    - `bmc_reference.md`: Osterwalder 9 blocks theoretical definitions and block relationship constraints.
    - `lean_canvas_guide.md`: Maurya Lean Canvas problem/solution/early adopter guidelines.
    - `startup_case_studies.md`: 15 vertical case studies (B2B SaaS, marketplace, fintech, direct-to-consumer, AI developer tooling).
    - `porter_swot_guide.md`: Porter's 5 Forces and SWOT framework references.
- [ ] **2.5 Implement ChromaDB Vector Store & Embedding Manager**
  - **Files:** [`services/business_intelligence/app/rag/vector_store.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/rag/vector_store.py), [`embeddings.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/rag/embeddings.py)
  - **Task:** Configure ChromaDB client with persistent disk volume mount (`./data/chroma`). Implement embedding generation using `sentence-transformers/all-MiniLM-L6-v2` (or OpenAI `text-embedding-3-small` fallback).
- [ ] **2.6 Implement Hybrid Retriever with MMR Diversity**
  - **File:** [`services/business_intelligence/app/rag/retriever.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/rag/retriever.py)
  - **Task:** Query expansion + cosine similarity search ($k=5$) + Maximal Marginal Relevance (MMR, $\lambda=0.7$) to retrieve top 3 diverse framework chunks per canvas block.

### 3. Business Model Agent (RAG-Powered)
- [ ] **2.7 Implement Business Model Generation Agent**
  - **File:** [`services/business_intelligence/app/agents/business_model/agent.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/agents/business_model/agent.py)
  - **Task:** Consume `IdeaAnalysisOutput` + `MarketResearchOutput`, query RAG retriever for relevant blocks, synthesize complete 9-block Business Model Canvas.
- [ ] **2.8 Implement Canvas Builder & Verification**
  - **File:** [`services/business_intelligence/app/agents/business_model/canvas_builder.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/agents/business_model/canvas_builder.py)
  - **Task:** Construct [`BusinessModelCanvas`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/business_model.py) object, verify consistency between value proposition, cost structure, and revenue streams.
- [ ] **2.9 Wire Up Public Interface**
  - **File:** [`services/business_intelligence/app/interface.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/app/interface.py)
  - **Task:** Replace hardcoded mocks in `run_idea_analysis` and `run_business_model` with real agent invocations.
- [ ] **2.10 Write Domain Unit Tests**
  - **Directory:** [`services/business_intelligence/tests/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/business_intelligence/tests)
  - **Tasks:**
    - `test_idea_analysis.py`: Test assumption deconstruction with mock LLM outputs.
    - `test_rag_seeding.py`: Verify idempotent ChromaDB seeding and query retrieval count.
    - `test_business_model.py`: Test canvas synthesis with retrieved context.

---

## 👤 Member 3: Market Research, Web Scraping & Critic / Evidence Validation

**Domain Lead:** Member 3  
**Primary Directory:** [`services/research/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research)  
**Shared Dependencies:** [`shared/contracts/market.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/market.py), [`shared/contracts/critic.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/critic.py)

### 1. Market Research Tools & Web Scraping
- [ ] **3.1 Implement Live Web Search Tool (Tavily Integration)**
  - **File:** [`services/research/app/tools/web_search.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/tools/web_search.py)
  - **Task:** Implement `TavilySearchTool` querying live web for competitor data, market size (TAM/SAM/SOM), industry growth rates (CAGR), and regulatory hurdles.
  - **Fallback:** If `TAVILY_API_KEY` is missing or network fails, gracefully degrade to cached fixtures or parameterized model knowledge with clear warning flags.
- [ ] **3.2 Implement Search Cache with Redis (24-Hour TTL)**
  - **File:** [`services/research/app/tools/search_cache.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/tools/search_cache.py)
  - **Task:** Normalize search queries, generate SHA-256 hash keys, cache results in Redis for 24 hours to prevent repeated API cost and speed up re-planning runs.
- [ ] **3.3 Implement Web Page Scraper & Source Parser**
  - **File:** [`services/research/app/tools/source_parser.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/tools/source_parser.py)
  - **Task:** Lightweight BeautifulSoup scraper to parse competitor landing pages, extract pricing tiers, feature lists, and company taglines.

### 2. Market Research Agent & Market Sizing
- [ ] **3.4 Implement Market Research Agent Core**
  - **File:** [`services/research/app/agents/market_research/agent.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/agents/market_research/agent.py)
  - **Task:** Orchestrate web queries based on `IdeaAnalysisOutput`; identify 3–5 competitors; extract pricing; synthesize market trends and entry barriers.
  - **Targeted Re-planning Awareness:** When `critique_history` is provided, generate targeted search queries specifically resolving prior unverified claims.
- [ ] **3.5 Implement Deterministic Market Sizing Engine**
  - **File:** [`services/research/app/agents/market_research/market_sizing.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/agents/market_research/market_sizing.py)
  - **Task:** Triangulate TAM, SAM, and SOM using top-down industry reports combined with bottom-up customer counts $\times$ pricing. Enforce preliminary $SOM \le SAM \le TAM$ invariant before returning.
- [ ] **3.6 Implement Market Research Prompts & Schemas**
  - **Files:** [`services/research/app/agents/market_research/prompts.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/agents/market_research/prompts.py), [`schemas.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/agents/market_research/schemas.py)
  - **Task:** Prompts strictly mapping claims to external URL citations.

### 3. Critic & Evidence Validation Agent
- [ ] **3.7 Implement Strict 3-Point Critic Rubric Engine**
  - **File:** [`services/research/app/critic/critic.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/critic/critic.py)
  - **Task:** Evaluate [`MarketResearchOutput`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/market.py) against:
    1. `confidence_score >= 0.70`
    2. `verified_sources_count >= 2`
    3. `len(unsupported_claims) == 0`
  - **Output:** Emits [`CriticValidationOutput`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/critic.py) with `ValidationStatus` (`VALID`, `LOW_CONFIDENCE`, `RESEARCH_REQUIRED`, `REANALYSIS_REQUIRED`).
- [ ] **3.8 Implement Citation & Competitor Validation Checks**
  - **Files:** [`services/research/app/critic/citation_validator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/critic/citation_validator.py), [`competitor_checker.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/critic/competitor_checker.py), [`evidence_validator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/critic/evidence_validator.py)
  - **Task:** Verify URL formatting, check domain reputation, cross-reference market claims against citations, flag ungrounded market claims.
- [ ] **3.9 Implement Composite Confidence Scoring Formula**
  - **File:** [`services/research/app/critic/confidence.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/critic/confidence.py)
  - **Task:** Calculate composite confidence: weighted combination of citation count, competitor detail depth, and market sizing source verification.
- [ ] **3.10 Wire Up Public Interface**
  - **File:** [`services/research/app/interface.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/app/interface.py)
  - **Task:** Replace mock return objects in `run_market_research` and `run_critic_validation` with real agent executions.
- [ ] **3.11 Write Domain Unit Tests**
  - **Directory:** [`services/research/tests/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/research/tests)
  - **Tasks:**
    - `test_web_search.py`: Test Tavily search and Redis caching behavior.
    - `test_critic_rubric.py`: Test pass/fail thresholds against synthetic valid and invalid market reports.
    - `test_market_sizing.py`: Test invariant boundary checks ($SOM \le SAM \le TAM$).

---

## 👤 Member 4: Revenue Estimation & Deterministic Financial Engine

**Domain Lead:** Member 4  
**Primary Directory:** [`services/finance/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance)  
**Shared Dependencies:** [`shared/contracts/revenue.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/revenue.py)

### 1. Phase 1: Parameter Extraction (LLM)
- [ ] **4.1 Implement Parameter Extraction Agent**
  - **File:** [`services/finance/app/agents/revenue_estimation/agent.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/agents/revenue_estimation/agent.py)
  - **Task:** LLM analyzes `IdeaAnalysisOutput`, `MarketResearchOutput`, and `BusinessModelOutput` to extract concrete numerical parameters:
    - Base monthly subscription price / ARPU ($)
    - Starting customer count ($m_1$)
    - Monthly organic & paid acquisition growth rates
    - Customer churn rate ($0.0 \le r \le 1.0$)
    - COGS per customer / gross margin percentage
    - Customer Acquisition Cost (CAC)
    - Initial starting capital / funding
    - Monthly fixed operational overhead (OPEX)
- [ ] **4.2 Implement Parameter Extraction Prompts & Schemas**
  - **Files:** [`services/finance/app/agents/revenue_estimation/prompts.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/agents/revenue_estimation/prompts.py), [`schemas.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/agents/revenue_estimation/schemas.py)
  - **Task:** Structured JSON extraction with strict validation against negative or absurd numbers.

### 2. Phase 2: Deterministic Python Math Engine
- [ ] **4.3 Implement Complete Core Financial Calculator**
  - **File:** [`services/finance/app/engine/calculator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/engine/calculator.py)
  - **Task:** Replace basic 14-line stub with full mathematical formulas:
    - $\text{Active Users}_m = \text{Active Users}_{m-1} \times (1 - \text{Churn}) + \text{Acquired}_m$
    - $\text{MRR}_m = \text{Active Users}_m \times \text{ARPU}_m$
    - $\text{ARR}_m = \text{MRR}_m \times 12$
    - $\text{Gross Profit}_m = \text{MRR}_m \times (1 - \text{COGS Rate})$
    - $\text{Net Burn}_m = (\text{Fixed OPEX} + (\text{Acquisitions}_m \times \text{CAC})) - \text{Gross Profit}_m$
    - $\text{Cash Reserve}_m = \text{Cash Reserve}_{m-1} - \text{Net Burn}_m$
    - $\text{Runway}_m = \frac{\text{Cash Reserve}_m}{\max(1, \text{Net Burn}_m)}$
- [ ] **4.4 Implement 12-to-36 Month Projections Generator**
  - **File:** [`services/finance/app/engine/projections.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/engine/projections.py)
  - **Task:** Build tabular month-by-month projection dictionary array across 12, 24, and 36 months horizon.
- [ ] **4.5 Implement Three-Scenario Simulation Engine**
  - **File:** [`services/finance/app/engine/scenario_engine.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/engine/scenario_engine.py)
  - **Task:** Compute deterministic projections across 3 distinct scenarios:
    - **Conservative:** Growth rate $\times 0.7$, churn rate $\times 1.3$, CAC $\times 1.25$
    - **Moderate:** Baseline extracted parameters
    - **Optimistic:** Growth rate $\times 1.4$, churn rate $\times 0.8$, CAC $\times 0.85$
- [ ] **4.6 Implement Unit Economics & Sensitivity Engine**
  - **Files:** [`services/finance/app/engine/unit_economics.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/engine/unit_economics.py), [`sensitivity.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/engine/sensitivity.py)
  - **Task:** Calculate LTV ($\frac{\text{ARPU} \times \text{Gross Margin}}{\text{Churn}}$), LTV:CAC ratio, CAC payback period (months), and sensitivity matrix (price $\pm 20\%$, churn $\pm 20\%$).

### 3. Boundary & Invariant Validation
- [ ] **4.7 Implement Boundary & Financial Invariant Validator**
  - **Files:** [`services/finance/app/validation/boundary_checks.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/validation/boundary_checks.py), [`invariants.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/validation/invariants.py), [`financial_validator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/validation/financial_validator.py)
  - **Task:** Implement hard validation rules:
    1. $\text{SOM} \le \text{SAM} \le \text{TAM}$
    2. $\text{Gross Margin} > 0$
    3. $0.0 \le \text{Monthly Churn} \le 1.0$
    4. $\text{LTV} / \text{CAC} \ge 3.0$ (or emit structural warning flag)
    5. Non-negative constraints ($\text{Price} \ge 0$, $\text{CAC} \ge 0$, $\text{Starting Capital} \ge 0$)
- [ ] **4.8 Wire Up Public Interface**
  - **File:** [`services/finance/app/interface.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/app/interface.py)
  - **Task:** Integrate parameter extraction agent with calculator and scenario engine; return fully populated [`RevenueEstimationOutput`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/revenue.py).
- [ ] **4.9 Expand Math Engine Unit Tests**
  - **Directory:** [`services/finance/tests/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/tests)
  - **Files:** [`test_calculator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/tests/test_calculator.py), [`test_boundaries.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/tests/test_boundaries.py), [`test_projection.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/finance/tests/test_projection.py)
  - **Tasks:** Add property-based tests checking zero-division protection, negative number rejection, and scenario monotonicity.

---

## 👤 Member 5: Marketing Strategy, Startup Roadmap & Document Exporters

**Domain Lead:** Member 5  
**Primary Directory:** [`services/marketing_output/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output)  
**Shared Dependencies:** [`shared/contracts/marketing.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/marketing.py), [`shared/contracts/roadmap.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/roadmap.py)

### 1. Marketing & GTM Agent (Bullseye Framework)
- [ ] **5.1 Polish & Verify Traction Channel Allocation**
  - **Files:** [`services/marketing_output/app/agents/marketing/channel_selector.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/agents/marketing/channel_selector.py), [`budget_allocator.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/agents/marketing/budget_allocator.py), [`archetypes.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/agents/marketing/archetypes.py)
  - **Status:** Core logic written; verify mathematical alignment between budget allocations and financial CAC targets.
- [ ] **5.2 Verify 12-Week (90-Day) Sprint Plan Generator**
  - **File:** [`services/marketing_output/app/agents/marketing/gtm_plan.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/agents/marketing/gtm_plan.py)
  - **Task:** Verify week-by-week sequencing (Weeks 1–4: Foundation & Tracking; Weeks 5–8: Alpha Traction; Weeks 9–12: Scale & Optimization) with clear KPIs and founder actions.

### 2. Startup Roadmap Synthesis
- [ ] **5.3 Implement Unified Roadmap Synthesis Agent**
  - **File:** [`services/marketing_output/app/interface.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/interface.py) (function `run_roadmap_synthesis`)
  - **Task:** Consolidate outputs from Idea Analysis, Market Research, Critic, Business Model, Revenue Estimation, and Marketing Plan into an executive [`StartupRoadmap`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/shared/contracts/roadmap.py).
  - **Requirements:**
    - Synthesize 4 phased execution milestones (Phase 1: Validation $\rightarrow$ Phase 2: MVP $\rightarrow$ Phase 3: Launch $\rightarrow$ Phase 4: Scale).
    - Top 5 cross-functional venture risks with concrete mitigations.
    - Composite overall confidence score calculation.

### 3. Document Export Engines (PDF & DOCX)
- [ ] **5.4 Implement ReportLab Executive PDF Exporter**
  - **File:** [`services/marketing_output/app/export/pdf_exporter.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/export/pdf_exporter.py)
  - **Task:** Build multi-page PDF generation using ReportLab:
    - Cover page with venture title, founder details, and generated timestamp.
    - Executive summary & confidence score badge.
    - 9-block Business Model Canvas layout table.
    - Competitor comparison matrix with live citations.
    - 12-month financial projection table (Conservative / Moderate / Optimistic).
    - 90-day GTM milestone calendar.
- [ ] **5.5 Implement python-docx Editable Word Exporter**
  - **File:** [`services/marketing_output/app/export/docx_exporter.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/export/docx_exporter.py)
  - **Task:** Generate structured `.docx` file allowing founders to edit and customize their business plan for pitch decks and grant applications.
- [ ] **5.6 Implement HTML / Markdown Export Renderer**
  - **File:** [`services/marketing_output/app/export/roadmap_renderer.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/export/roadmap_renderer.py)
  - **Task:** Render standalone responsive HTML report from [`roadmap_template.html`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/app/export/templates/roadmap_template.html).
- [ ] **5.7 Add Export REST Endpoints to Orchestrator API**
  - **File:** [`services/orchestrator/app/api/routes.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/orchestrator/app/api/routes.py)
  - **Task:** Add endpoints `GET /api/ventures/{id}/export/pdf` and `GET /api/ventures/{id}/export/docx` returning file download streams with proper MIME types.
- [ ] **5.8 Fix Marketing Agent Unit Tests & Add Export Tests**
  - **Files:** [`services/marketing_output/tests/test_marketing_agent.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/services/marketing_output/tests/test_marketing_agent.py), `test_exporters.py`
  - **Task:** Fix module imports so test runs cleanly; add test asserting PDF and DOCX binary generation without errors.

---

## 💻 Frontend Dashboard & User Interface (Next.js 14)

**Primary Directory:** [`apps/frontend/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend)  
**Lead Collaborators:** Member 5 & Member 1

- [ ] **F.1 Complete Venture Wizard Form**
  - **File:** [`apps/frontend/src/app/startup/new/page.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/app/startup/new/page.tsx)
  - **Task:** Collect startup idea, target audience, problem statement, geography, budget, and timeline. Submit via `POST /api/ventures/start` and redirect to `/startup/[startupId]`.
- [ ] **F.2 Wire Live Progress Bar & Stage Indicator**
  - **Files:** [`apps/frontend/src/components/AgentProgress.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/AgentProgress.tsx), [`useAgentStream.ts`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/hooks/useAgentStream.ts)
  - **Task:** Render dynamic 7-stage stepper showing active agent, completed stages, live percentage (0-100%), and streaming status messages.
- [ ] **F.3 Build Human-in-the-Loop Review Modal Banner**
  - **File:** [`apps/frontend/src/components/HitlReviewBanner.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/HitlReviewBanner.tsx)
  - **Task:** When `HITL_REQUIRED` event is received or `state.human_review_required == true`:
    - Display critic warnings and failed assumptions.
    - Provide 3 action buttons: "Proceed Anyway (Accept Risk)", "Override Assumptions", and "Abort Pipeline".
    - Send payload to `POST /api/ventures/{id}/review` and resume streaming.
- [ ] **F.4 Implement Interactive Business Model Canvas Viewer**
  - **File:** [`apps/frontend/src/components/results/BusinessModelView.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/results/BusinessModelView.tsx)
  - **Task:** 9-box grid layout presenting Osterwalder blocks (Partners, Activities, Resources, Value Props, Customer Relationships, Channels, Segments, Cost Structure, Revenue Streams).
- [ ] **F.5 Implement Market Research & Citation Cards**
  - **File:** [`apps/frontend/src/components/results/MarketResearchView.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/results/MarketResearchView.tsx)
  - **Task:** Competitor comparison cards, TAM/SAM/SOM summary badges, and clickable external source citation links.
- [ ] **F.6 Implement Financial Projections & Scenario Toggle Chart**
  - **Files:** [`apps/frontend/src/components/RevenueChart.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/RevenueChart.tsx), [`RevenueProjectionsView.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/results/RevenueProjectionsView.tsx)
  - **Task:** Interactive multi-line chart (Recharts or Chart.js) toggling Conservative, Moderate, and Optimistic 12-month MRR/ARR trajectories, plus key metrics (CAC, LTV, Runway, Break-Even month).
- [ ] **F.7 Implement 90-Day Roadmap Sprint Viewer**
  - **File:** [`apps/frontend/src/components/results/MarketingRoadmapView.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/results/MarketingRoadmapView.tsx)
  - **Task:** Phased 12-week timeline view grouped into 3 monthly milestones with weekly KPI checklists.
- [ ] **F.8 Wire Up PDF & Word Document Download Buttons**
  - **File:** [`apps/frontend/src/components/results/RoadmapView.tsx`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/apps/frontend/src/components/results/RoadmapView.tsx)
  - **Task:** Connect "Download PDF Report" and "Download Word Roadmap" buttons to backend export endpoints with loading spinners.

---

## 📈 Evaluation Harness & Academic Benchmarks

**Primary Directory:** [`evaluation/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation)  
**Lead Collaborator:** Member 3

- [ ] **E.1 Implement Benchmark Evaluation Runner**
  - **File:** `evaluation/run.py`
  - **Task:** Build automated evaluation script that runs the 4 benchmark scenarios (`valid_startup.json`, `weak_market.json`, `invalid_finance.json`, `api_failure.json`), computes all 5 quantitative metrics, and prints a formatted summary table.
- [ ] **E.2 Implement Citation Rate Metric (Target: 100%)**
  - **File:** [`evaluation/metrics/citation_rate.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation/metrics/citation_rate.py)
  - **Formula:** $\frac{\text{verified\_external\_citations}}{\text{total\_factual\_market\_claims}}$
- [ ] **E.3 Implement Schema Compliance Metric (Target: > 95%)**
  - **File:** [`evaluation/metrics/schema_compliance.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation/metrics/schema_compliance.py)
  - **Formula:** $\frac{\text{valid\_pydantic\_contract\_outputs}}{\text{total\_agent\_invocations}}$
- [ ] **E.4 Implement Workflow Completion Metric (Target: $\ge$ 90%)**
  - **File:** [`evaluation/metrics/workflow_completion.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation/metrics/workflow_completion.py)
  - **Formula:** $\frac{\text{ventures\_reaching\_COMPLETED}}{\text{total\_ventures\_started}}$
- [ ] **E.5 Implement End-to-End Latency Metric (Target: < 8 min)**
  - **File:** [`evaluation/metrics/latency.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation/metrics/latency.py)
  - **Formula:** $t_{\text{ROADMAP\_READY}} - t_{\text{POST\_START}}$
- [ ] **E.6 Implement Token & Dollar Cost Tracking Metric**
  - **File:** [`evaluation/metrics/cost.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation/metrics/cost.py)
  - **Formula:** $\sum (\text{tokens}_{\text{prompt}} \cdot c_p + \text{tokens}_{\text{comp}} \cdot c_c)$
- [ ] **E.7 Complete Evaluation Scenario Fixtures**
  - **Files:** [`evaluation/scenarios/valid_startup.json`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/evaluation/scenarios/valid_startup.json), `weak_market.json`, `invalid_finance.json`, `api_failure.json`
  - **Task:** Verify test fixture contents simulate specific failure/success trigger conditions.

---

## 🧪 Comprehensive Testing Suite

**Primary Directory:** [`tests/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/tests)  
**Lead Collaborator:** Member 4

- [ ] **T.1 Re-implement Shared Contract Tests**
  - **File:** `tests/contracts/test_contracts.py`
  - **Task:** Test validation rules across all Pydantic v2 contracts (`FounderInput`, `IdeaAnalysisOutput`, `MarketResearchOutput`, `CriticValidationOutput`, `BusinessModelOutput`, `RevenueEstimationOutput`, `MarketingPlanOutput`, `StartupRoadmap`, `VentureState`).
- [ ] **T.2 Implement Happy Path Integration Test (Scenario A)**
  - **File:** [`tests/integration/test_happy_path.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/tests/integration/test_happy_path.py)
  - **Task:** Replace dummy `assert True` with full mock execution of LangGraph pipeline asserting transition through all 7 stages to `COMPLETED`.
- [ ] **T.3 Implement Targeted Re-planning Integration Test (Scenario B)**
  - **File:** [`tests/integration/test_replanning_path.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/tests/integration/test_replanning_path.py)
  - **Task:** Inject low-confidence critic evaluation; assert state machine re-routes specifically to `market_research` with incremented `replan_count` and populated `critique_history`.
- [ ] **T.4 Implement Failure & HITL Recovery Integration Test (Scenario C)**
  - **File:** [`tests/integration/test_failure_recovery.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/tests/integration/test_failure_recovery.py)
  - **Task:** Simulate $> 5$ replans; assert transition to `human_review_node`; submit `POST /review` resume action; assert pipeline unpauses and completes.
- [ ] **T.5 Implement End-to-End System Test**
  - **File:** [`tests/e2e/test_full_startup_flow.py`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/tests/e2e/test_full_startup_flow.py)
  - **Task:** Use FastAPI `TestClient` to test full startup flow: submit founder idea $\rightarrow$ poll state $\rightarrow$ verify generated roadmap and financial numbers.

---

## 📚 Documentation & Project Deliverables

**Primary Directory:** [`docs/`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs)  
**Lead Collaborators:** All Members

- [ ] **D.1 Populate Agent Workflows Document**
  - **File:** [`docs/agent-workflows.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/agent-workflows.md)
  - **Task:** Document state machine transitions, node responsibilities, re-planning triggers, and sequence diagrams.
- [ ] **D.2 Populate API Contracts Document**
  - **File:** [`docs/api-contracts.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/api-contracts.md)
  - **Task:** Document all REST endpoints (`POST /start`, `GET /{id}`, `POST /{id}/review`, `GET /{id}/stream`, `GET /{id}/export/*`), request/response JSON schemas, and error codes.
- [ ] **D.3 Populate Demo Scenarios Walkthrough**
  - **File:** [`docs/demo-scenarios.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/demo-scenarios.md)
  - **Task:** Document step-by-step presentation scripts for:
    - **Scenario A (Happy Path):** B2B SaaS Workflow Tool — passes all gates smoothly.
    - **Scenario B (Critic Re-planning):** D2C Beverage Startup — weak claims caught by Critic, triggers web research self-healing.
    - **Scenario C (HITL & Financial Retuning):** DeepTech Hardware — financial discrepancy triggers retune and HITL pause.
- [ ] **D.4 Populate Local Setup & Deployment Guide**
  - **File:** [`docs/setup.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/setup.md)
  - **Task:** Document prerequisites, `.env` file configuration, Docker Compose commands, virtualenv editable installs, database seeding, and troubleshooting.
- [ ] **D.5 Populate Venture State Blackboard Specification**
  - **File:** [`docs/venture-state.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/venture-state.md)
  - **Task:** Detailed breakdown of all fields in `VentureState`, stage progression rules, and critique history schemas.

---

## 🎯 Priority Execution Matrix & Milestones

| Milestone | Deliverables | Target Date | Primary Owners |
| :--- | :--- | :--- | :--- |
| **Milestone 1: Clean Foundation** | Fix folder renames, fix pytest collection error, create contract tests | **Week 1** | Member 1 & Member 4 |
| **Milestone 2: Deterministic Engines** | Complete financial calculator, boundary checks, ReportLab PDF, python-docx | **Week 2** | Member 4 & Member 5 |
| **Milestone 3: Agent Intelligence & Tools** | Implement Tavily search, Redis cache, Critic rubric, ChromaDB RAG BMC agent | **Week 3** | Member 2 & Member 3 |
| **Milestone 4: Central Orchestration** | LangGraph StateGraph, conditional edges, self-healing re-planning, Redis SSE | **Week 4** | Member 1 |
| **Milestone 5: Frontend Experience** | Complete Next.js dashboard, SSE streaming, interactive canvas, HITL modal | **Week 5** | Member 5 & Member 1 |
| **Milestone 6: Verification & Defense** | Integration tests, evaluation benchmark suite (all 5 metrics), demo rehearsals | **Week 6** | All Team Members |

---

*For technical architecture details, refer to [`docs/architecture.md`](file:///home/savindust/Documents/projects/ai-co-founder/ai-cofounder/docs/architecture.md).*
