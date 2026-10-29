from shared.contracts.business_model import BusinessModelCanvas, BusinessModelOutput
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import Competitor, MarketResearchOutput

try:
    from services.finance.app.interface import run_revenue_estimation
except ImportError:
    from app.interface import run_revenue_estimation


def _inputs(som=50_000_000.0):
    idea = IdeaAnalysisOutput(
        problem_statement="Students need reliable laundry pickup",
        target_users=["University students"],
        refined_value_proposition="Scheduled laundry pickup and delivery",
        key_assumptions=["Students value time savings"],
        clarity_score=0.9,
        feasibility_score=0.85,
        confidence_score=0.85,
    )
    market = MarketResearchOutput(
        competitor_landscape=[Competitor(name="CleanGo", description="Laundry app", pricing_model="$25/mo")],
        customer_personas=[],
        market_trends=[],
        entry_barriers=[],
        tam_estimate=500_000_000.0,
        sam_estimate=100_000_000.0,
        som_estimate=som,
        confidence_score=0.85,
    )
    business = BusinessModelOutput(
        canvas=BusinessModelCanvas(
            revenue_streams=["$19/mo student subscription"],
            cost_structure=["Pickup logistics", "Partner laundries"],
        ),
        confidence_score=0.85,
    )
    founder = FounderInput(startup_idea="Laundry pickup", target_market="Student Services", budget=150000.0)
    return idea, market, business, founder


def test_interface_returns_complete_output():
    idea, market, business, founder = _inputs()
    output = run_revenue_estimation(idea, market, business, founder=founder)

    assert output.tam_sam_som_valid is True
    assert len(output.scenarios) == 3
    assert output.unit_economics is not None
    assert output.unit_economics.ltv > 0
    assert output.unit_economics.ltv_cac_ratio > 0
    assert output.sensitivity is not None
    assert len(output.sensitivity.cells) == 9
    assert output.horizon_months == 12
    assert output.invariant_violations == []
    assert all(len(s.monthly_projections) == 12 for s in output.scenarios)


def test_interface_honors_horizon_and_retune_context():
    idea, market, business, founder = _inputs()
    output = run_revenue_estimation(
        idea,
        market,
        business,
        horizon_months=24,
        founder=founder,
        critique_notes="LTV:CAC too low in prior iteration",
        retune_round=1,
    )
    assert output.horizon_months == 24
    assert all(len(s.monthly_projections) == 24 for s in output.scenarios)


def test_interface_surfaces_invalid_market_invariant():
    idea, market, business, founder = _inputs(som=900_000_000.0)
    output = run_revenue_estimation(idea, market, business, founder=founder)

    assert output.tam_sam_som_valid is False
    assert any("Market sizing invariant" in violation for violation in output.invariant_violations)
