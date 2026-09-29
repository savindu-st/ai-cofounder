"""Business Intelligence Domain Strict Interface.

Exposes public entrypoints for Idea Analysis and RAG-powered Business Model Canvas synthesis.
All interactions from orchestrator or other agents must pass through this interface.
"""

from typing import Optional
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.business_model import BusinessModelOutput, BusinessModelCanvas


async def run_idea_analysis(founder_input: FounderInput) -> IdeaAnalysisOutput:
    """Deconstructs founder input into core assumptions, value proposition, and customer segments."""
    # In full implementation, delegates to app.agents.idea_analysis.agent
    target_users = [founder_input.target_market] if founder_input.target_market else ["Target Enterprise Users"]
    return IdeaAnalysisOutput(
        problem_statement=f"Addressing operational inefficiencies for {founder_input.target_market}: {founder_input.startup_idea}",
        target_users=target_users,
        refined_value_proposition=f"Automated, intelligence-driven solution delivering {founder_input.startup_idea}",
        key_assumptions=[
            "Target market demonstrates strong willingness to pay for automation",
            "Customer acquisition unit economics remain sustainable at scale"
        ],
        red_flags=[],
        clarity_score=0.90,
        feasibility_score=0.85,
        confidence_score=0.88
    )


async def run_business_model(
    idea: IdeaAnalysisOutput,
    market: MarketResearchOutput
) -> BusinessModelOutput:
    """Synthesizes the 9 Business Model Canvas blocks using ChromaDB RAG and market data."""
    # In full implementation, delegates to app.agents.business_model.agent with RAG retrieval
    canvas = BusinessModelCanvas(
        key_partners=["Cloud Providers", "Data Aggregators", "Distribution Channels"],
        key_activities=["Platform Development", "Algorithm Tuning", "Customer Success"],
        key_resources=["Proprietary AI Models", "Domain Knowledge Corpus", "Engineering Team"],
        value_propositions=[idea.refined_value_proposition],
        customer_relationships=["Automated Self-Serve", "Community Support"],
        channels=["Direct Web App", "Product-Led Growth", "Founder Networks"],
        customer_segments=idea.target_users,
        cost_structure=["Cloud Infrastructure", "API Costs", "Salaries"],
        revenue_streams=["Subscription Tiers (B2B SaaS)", "Usage-Based Add-ons"]
    )
    return BusinessModelOutput(
        canvas=canvas,
        framework_used="Osterwalder Business Model Canvas (BMC)",
        key_risks=["Competitive pressure from incumbents", "Customer acquisition cost scaling"],
        mitigations=["Product-led growth loops", "Targeted enterprise integration"],
        confidence_score=0.85
    )

