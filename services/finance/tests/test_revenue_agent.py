from shared.contracts.business_model import BusinessModelCanvas, BusinessModelOutput
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import Competitor, MarketResearchOutput

try:
    from services.finance.app.agents.revenue_estimation.agent import RevenueParameterAgent
    from services.finance.app.agents.revenue_estimation.schemas import ExtractedFinancialParameters
except ImportError:
    from app.agents.revenue_estimation.agent import RevenueParameterAgent
    from app.agents.revenue_estimation.schemas import ExtractedFinancialParameters


def _idea():
    return IdeaAnalysisOutput(
        problem_statement="Engineering teams need faster automated code review",
        target_users=["Engineering Managers", "Developers"],
        refined_value_proposition="AI code review agent for pull requests",
        key_assumptions=["Teams pay per seat"],
        clarity_score=0.9,
        feasibility_score=0.9,
        confidence_score=0.88,
    )


def _market():
    return MarketResearchOutput(
        competitor_landscape=[
            Competitor(name="ReviewBot", description="AI review", pricing_model="$49/seat/mo"),
            Competitor(name="CodeGuard", description="Static analysis", pricing_model="$99/seat/mo"),
        ],
        customer_personas=[],
        market_trends=[],
        entry_barriers=[],
        tam_estimate=8_000_000_000.0,
        sam_estimate=1_000_000_000.0,
        som_estimate=50_000_000.0,
        confidence_score=0.9,
    )


def _business_model():
    return BusinessModelOutput(
        canvas=BusinessModelCanvas(
            revenue_streams=["B2B SaaS subscription at $79/seat/mo"],
            cost_structure=["Cloud compute", "Engineering salaries"],
        ),
        confidence_score=0.9,
    )


def _founder():
    return FounderInput(
        startup_idea="AI code review agent",
        target_market="Developer Tools",
        budget=50000.0,
    )


def test_deterministic_fallback_extracts_viable_parameters():
    agent = RevenueParameterAgent(llm=None)
    result = agent.extract(_idea(), _market(), _business_model(), _founder())

    assert isinstance(result, ExtractedFinancialParameters)
    assert result.monthly_price > 0
    assert result.starting_customers >= 5
    assert 0 <= result.monthly_growth_rate <= 1
    assert 0 <= result.monthly_churn_rate <= 1
    assert result.cogs_per_unit < result.monthly_price
    assert result.cac > 0
    assert result.starting_capital == 50000.0


def test_llm_extraction_is_sanitized():
    class MockLLM:
        def generate_json(self, prompt, schema):
            return {
                "monthly_price": 120,
                "starting_customers": 40,
                "monthly_growth_rate": 0.1,
                "monthly_churn_rate": 0.02,
                "cogs_per_unit": 20,
                "fixed_monthly_costs": 4000,
                "cac": 150,
                "starting_capital": 30000,
                "assumptions": ["mock"],
                "confidence": 0.8,
            }

    agent = RevenueParameterAgent(llm=MockLLM())
    result = agent.extract(_idea(), _market(), _business_model(), _founder())
    assert result.monthly_price == 120
    assert result.starting_customers == 40
    assert result.assumptions == ["mock"]


def test_invalid_llm_output_falls_back():
    class BadLLM:
        def generate_json(self, prompt, schema):
            return {"monthly_price": "not-a-number"}

    agent = RevenueParameterAgent(llm=BadLLM())
    result = agent.extract(_idea(), _market(), _business_model(), _founder())
    assert result.monthly_price > 0
    assert result.starting_customers >= 5


def test_retune_round_tightens_unit_economics():
    agent = RevenueParameterAgent(llm=None)
    base = agent.extract(_idea(), _market(), _business_model(), _founder())
    retuned = agent.extract(_idea(), _market(), _business_model(), _founder(), retune_round=2)

    assert retuned.monthly_price > base.monthly_price
    assert retuned.monthly_churn_rate <= base.monthly_churn_rate
    assert retuned.cac < base.cac
