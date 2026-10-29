"""Prompt Templates for Market Research Agent.

Enforces strict external source attribution, competitor depth, and market sizing sanity.
Includes targeted re-planning prompt adaptations when critique feedback is provided.
"""

MARKET_RESEARCH_SYSTEM_PROMPT = """You are a Principal Venture Capital Market Intelligence Analyst and Strategic Researcher.
Your mission is to rigorously analyze market opportunities, competitive landscapes, customer willingness-to-pay, and market sizing (TAM, SAM, SOM) for new startup ventures.

CRITICAL OPERATING PRINCIPLES:
1. CITATION DISCIPLINE: Every factual claim in `supporting_evidence` must link directly to an external source from the provided web research context. Never invent URLs or use generic placeholders (e.g. example.com, test.com).
2. COMPETITOR DEPTH: Analyze 3-5 competitors (direct and indirect). For each competitor, specify realistic pricing models, key differentiators, structural weaknesses, and public URLs.
3. MARKET SIZING INVARIANT: Your market sizing calculations MUST satisfy the fundamental economic law: 0 < SOM <= SAM <= TAM.
   - TAM: Total global addressable demand for the entire solution category.
   - SAM: Realistic demand within the venture's target geography and technical scope.
   - SOM: Serviceable obtainable market capture over Year 1 to 2.
4. RE-PLANNING RESPONSIVENESS: If previous critique notes are provided, you MUST directly address and resolve all unverified claims and source deficiencies flagged in the feedback.
"""

MARKET_RESEARCH_USER_TEMPLATE = """Please synthesize a comprehensive market research report for the following startup venture:

### VENTURE SPECIFICATIONS:
- Startup Idea: {startup_idea}
- Problem Statement: {problem_statement}
- Target Customer Segments: {target_users}
- Target Market: {target_market}
- Target Geography: {target_geography}
- Capital & Runway Context: Budget ${budget:,.2f}, Timeline {timeline_months} months

### LIVE WEB SEARCH & INTELLIGENCE CONTEXT:
{search_context}

### COMPETITOR SCRAPING & DEEP-DIVE CONTEXT:
{scraped_context}
{critique_context}

Return your complete analysis as a valid JSON object matching the MarketResearchSynthesis schema.
Ensure all source_urls are legitimate external domains found in the intelligence context, and all claims in supporting_evidence cite these sources.
"""

CRITIQUE_FEEDBACK_SECTION = """
### ⚠️ PREVIOUS CRITIC FEEDBACK & UNVERIFIED CLAIMS (MUST BE RESOLVED):
The previous validation attempt flagged the following deficiencies that you MUST specifically rectify in this iteration:
- Previous Status: {critic_status}
- Prior Confidence Score: {confidence_score:.2f}
- Specific Unsupported / Unverified Claims:
{unsupported_claims_list}
- Critic Feedback Notes: {feedback_notes}

INSTRUCTION: Explicitly replace or verify each flagged claim with hard data and direct citations from the search context.
"""
