"""Reusable venture fixtures for roadmap/export tests."""

from shared.contracts.business_model import BusinessModelCanvas, BusinessModelOutput
from shared.contracts.critic import CriticValidationOutput
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import Competitor, MarketResearchOutput
from shared.contracts.marketing import MarketingPlanOutput, Milestone
from shared.contracts.revenue import (
    FinancialParameters,
    ProjectionScenario,
    RevenueEstimationOutput,
    UnitEconomics,
)
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus


def build_sample_state() -> VentureState:
    founder = FounderInput(
        startup_idea="Enterprise CRM workflow automation platform",
        target_market="B2B Enterprise SaaS",
        target_geography="North America",
        budget=10000.0,
        timeline_months=3,
        goals="Acquire 10 enterprise pilot logos",
        constraints=["Requires SOC2 compliance"],
        skills_resources="Technical co-founder with enterprise sales experience",
    )
    idea = IdeaAnalysisOutput(
        problem_statement="Enterprise sales teams struggle with fragmented CRM data and slow workflow compliance.",
        target_users=["VP of Sales", "Enterprise Sales Operations", "Revenue Leaders"],
        refined_value_proposition="Automate B2B pipeline forecasting with deterministic CRM data intelligence.",
        key_assumptions=["Enterprise teams will pay $150/user/mo"],
        red_flags=[],
        clarity_score=0.9,
        feasibility_score=0.85,
        confidence_score=0.88,
    )
    market = MarketResearchOutput(
        competitor_landscape=[
            Competitor(
                name="Salesforce",
                description="Legacy enterprise CRM",
                strengths=["Market dominance"],
                weaknesses=["Bloated UX", "Slow implementation"],
            ),
            Competitor(
                name="HubSpot",
                description="Mid-market CRM suite",
                strengths=["Ease of use"],
                weaknesses=["Limited enterprise workflows"],
            ),
        ],
        customer_personas=[{"role": "VP Sales", "pain_point": "Manual pipeline updates"}],
        market_trends=["AI automation in B2B RevOps"],
        entry_barriers=["Enterprise security review"],
        tam_estimate=5_000_000_000.0,
        sam_estimate=1_200_000_000.0,
        som_estimate=48_000_000.0,
        supporting_evidence=["Enterprise CRM spending continues to grow."],
        source_urls=["https://example.com/market-report"],
        confidence_score=0.85,
    )
    canvas = BusinessModelCanvas(
        key_partners=["Cloud providers"],
        key_activities=["Platform engineering"],
        key_resources=["Sales team"],
        value_propositions=["Automated B2B CRM workflows"],
        customer_relationships=["Dedicated account managers"],
        channels=["Direct sales", "LinkedIn outbound", "Webinars"],
        customer_segments=["Mid-market and enterprise B2B SaaS"],
        cost_structure=["Hosting", "SDR payroll"],
        revenue_streams=["Annual B2B SaaS subscription licenses"],
    )
    business_model = BusinessModelOutput(
        canvas=canvas,
        framework_used="Business Model Canvas",
        key_risks=["Security review may delay enterprise deals."],
        mitigations=["Start SOC2 readiness before the first pilot."],
        confidence_score=0.85,
    )
    revenue = RevenueEstimationOutput(
        pricing_strategy="Tiered per-seat monthly subscription",
        parameters=FinancialParameters(
            monthly_price=120.0,
            starting_customers=10,
            monthly_growth_rate=0.15,
            monthly_churn_rate=0.02,
            cogs_per_unit=15.0,
            fixed_monthly_costs=5000.0,
        ),
        scenarios=[
            ProjectionScenario(scenario_name="conservative", month_12_revenue=28000.0, month_12_customers=220),
            ProjectionScenario(scenario_name="moderate", month_12_revenue=50000.0, month_12_customers=400),
            ProjectionScenario(scenario_name="optimistic", month_12_revenue=82000.0, month_12_customers=620),
        ],
        unit_economics=UnitEconomics(
            arpu=120.0,
            gross_margin=0.875,
            cac=960.0,
            ltv=6000.0,
            ltv_cac_ratio=6.25,
            cac_payback_months=8.0,
        ),
        assumptions_summary=["Monthly churn remains below 2%."],
        confidence_score=0.84,
    )
    milestones = [
        Milestone(
            month=min(3, ((week - 1) // 4) + 1),
            week=week,
            focus=f"Week {week} milestone",
            target_kpi=f"Week {week} KPI",
            deliverables=[f"Week {week} deliverable"],
        )
        for week in range(1, 13)
    ]
    marketing = MarketingPlanOutput(
        positioning_statement="The deterministic workflow layer for enterprise revenue teams.",
        priority_channels=["Direct Sales & Cold Outbound", "Search Engine Optimization (SEO)", "Content Marketing & Thought Leadership"],
        messaging_framework={"headline": "Workflow intelligence for enterprise revenue teams"},
        gtm_90_day_plan=milestones,
        acquisition_tactics=["Founder-led outbound", "Comparison content"],
        budget_allocation={"Direct Sales & Cold Outbound": 6000.0, "Search Engine Optimization (SEO)": 2500.0, "Content Marketing & Thought Leadership": 1500.0},
        prioritized_next_actions=["Build landing page", "Interview 10 prospects", "Launch alpha"],
        venture_archetype="B2B Enterprise SaaS",
        target_cac=960.0,
        estimated_ltv=6000.0,
        cac_payback_months=8.0,
        budget_breakdown_dollars={"Direct Sales & Cold Outbound": 6000.0, "Search Engine Optimization (SEO)": 2500.0, "Content Marketing & Thought Leadership": 1500.0},
    )
    return VentureState(
        venture_id="ven-export-test",
        founder_input=founder,
        idea_analysis=idea,
        market_research=market,
        market_validation=CriticValidationOutput(
            status=ValidationStatus.VALID,
            confidence_score=0.9,
            verified_sources_count=3,
        ),
        business_model=business_model,
        revenue_estimation=revenue,
        marketing_plan=marketing,
    )
