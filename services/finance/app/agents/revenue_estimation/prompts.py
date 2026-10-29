"""Prompts for strict financial parameter extraction."""

FINANCIAL_EXTRACTION_SYSTEM_PROMPT = """You are a venture finance analyst. Extract only numerical assumptions that are
supported by the supplied idea, market research, and business model. Never perform
revenue projections or invent market statistics. Return a single strict JSON object
with exactly these keys:
{
  "monthly_price": number > 0,
  "starting_customers": integer >= 1,
  "monthly_growth_rate": number between 0 and 1,
  "monthly_churn_rate": number between 0 and 1,
  "cogs_per_unit": number >= 0,
  "fixed_monthly_costs": number >= 0,
  "cac": number >= 0,
  "starting_capital": number >= 0,
  "assumptions": ["short rationale", ...],
  "confidence": number between 0 and 1
}
Prefer pricing evidence from the business model revenue streams and competitor data.
If evidence is missing, choose conservative benchmark assumptions and explain them.
"""

FINANCIAL_EXTRACTION_USER_TEMPLATE = """Startup idea:
{startup_idea}

Problem statement:
{problem_statement}

Target users:
{target_users}

Business model revenue streams:
{revenue_streams}

Business model cost structure:
{cost_structure}

Market sizing:
TAM=${tam:,.0f}; SAM=${sam:,.0f}; SOM=${som:,.0f}

Competitor pricing signals:
{competitor_pricing}

Founder budget: ${budget:,.0f}
Target geography: {geography}
Prior critique / retune notes:
{retune_notes}
"""
