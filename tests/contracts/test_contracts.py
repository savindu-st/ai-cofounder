"""Automated Pydantic v2 Contract Validation Tests.

Validates schema constraints, boundary conditions, serialization, and lifecycle
defaults for all shared contracts across domain modules.
"""

from datetime import datetime
import pytest
from pydantic import ValidationError

from shared.contracts.base import TimestampedContract
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import Competitor, MarketResearchOutput
from shared.contracts.critic import CriticValidationOutput
from shared.contracts.business_model import BusinessModelCanvas, BusinessModelOutput
from shared.contracts.revenue import (
    FinancialParameters,
    ProjectionScenario,
    RevenueEstimationOutput
)
from shared.contracts.marketing import Milestone, MarketingPlanOutput
from shared.contracts.roadmap import StartupRoadmap
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage


class TestContracts:
    """Rigorous validation test suite for all shared Pydantic v2 contracts."""

    def test_timestamped_contract_defaults(self):
        """Verifies default timestamp initialization and updated_at None default."""
        contract = TimestampedContract()
        assert isinstance(contract.created_at, datetime)
        assert contract.updated_at is None

    def test_founder_input_serialization(self):
        """Verifies FounderInput serialization and deserialization round-trip."""
        founder_input = FounderInput(
            startup_idea="AI copilot for university applicants",
            target_market="Higher Education",
            target_geography="Sri Lanka",
            budget=50000.0,
            timeline_months=3,
            goals="Reach 1,000 active students",
            constraints=["Low budget", "Student schedule"],
            skills_resources="Python, Next.js"
        )
        assert founder_input.startup_idea == "AI copilot for university applicants"
        assert founder_input.budget == 50000.0

        dumped = founder_input.model_dump()
        reconstructed = FounderInput(**dumped)
        assert reconstructed.startup_idea == founder_input.startup_idea
        assert reconstructed.budget == founder_input.budget
        assert founder_input == reconstructed

    def test_idea_analysis_output_boundaries(self):
        """Verifies score boundary enforcement (0.0 to 1.0) on IdeaAnalysisOutput."""
        valid = IdeaAnalysisOutput(
            problem_statement="Complex university application procedures",
            target_users=["High school graduates"],
            refined_value_proposition="Automate essay feedback and deadline tracking",
            key_assumptions=["Students need AI guidance", "Affordability is paramount"],
            clarity_score=0.9,
            feasibility_score=0.85,
            confidence_score=0.88
        )
        assert valid.clarity_score == 0.9

        # Scores exceeding 1.0 must raise ValidationError
        with pytest.raises(ValidationError):
            IdeaAnalysisOutput(
                problem_statement="Problem",
                target_users=["Users"],
                refined_value_proposition="Value",
                key_assumptions=["Assumptions"],
                clarity_score=1.5,
                feasibility_score=0.8,
                confidence_score=0.8
            )

        # Negative scores must raise ValidationError
        with pytest.raises(ValidationError):
            IdeaAnalysisOutput(
                problem_statement="Problem",
                target_users=["Users"],
                refined_value_proposition="Value",
                key_assumptions=["Assumptions"],
                clarity_score=-0.1,
                feasibility_score=0.8,
                confidence_score=0.8
            )

    def test_market_research_contracts(self):
        """Verifies Competitor and MarketResearchOutput structure and estimates."""
        competitor = Competitor(
            name="EdTech Rival",
            description="Established legacy counseling service",
            strengths=["Brand trust"],
            weaknesses=["Manual and expensive"],
            pricing_model="$200/consultation",
            website_url="https://example.com"
        )
        market = MarketResearchOutput(
            competitor_landscape=[competitor],
            customer_personas=[{"persona": "Applicant", "need": "Speed"}],
            market_trends=["Adoption of GenAI tools"],
            entry_barriers=["Institutional partnerships"],
            tam_estimate=10000000.0,
            sam_estimate=2000000.0,
            som_estimate=300000.0,
            supporting_evidence=["Public market analysis"],
            source_urls=["https://example.com/source"],
            confidence_score=0.85
        )
        assert len(market.competitor_landscape) == 1
        assert market.competitor_landscape[0].name == "EdTech Rival"
        assert market.tam_estimate == 10000000.0

    def test_critic_validation_contract(self):
        """Verifies CriticValidationOutput and ValidationStatus enum handling."""
        critic = CriticValidationOutput(
            status=ValidationStatus.VALID,
            confidence_score=0.85,
            unsupported_claims=[],
            verified_sources_count=2,
            feedback_notes="All metrics grounded.",
            requires_pivot=False,
            suggested_alternatives=[]
        )
        assert critic.status == ValidationStatus.VALID
        assert critic.confidence_score == 0.85

    def test_business_model_contract(self):
        """Verifies all 9 blocks of BusinessModelCanvas and BusinessModelOutput."""
        canvas = BusinessModelCanvas(
            key_partners=["Schools"],
            key_activities=["App development"],
            key_resources=["AI models"],
            value_propositions=["Automated guidance"],
            customer_relationships=["Self-service"],
            channels=["Web"],
            customer_segments=["Students"],
            cost_structure=["Hosting"],
            revenue_streams=["Subscriptions"]
        )
        bm_output = BusinessModelOutput(
            framework_used="Osterwalder BMC",
            canvas=canvas,
            key_risks=["Model hallucinations"],
            mitigations=["Deterministic checks"],
            confidence_score=0.9
        )
        assert len(bm_output.canvas.value_propositions) == 1
        assert bm_output.confidence_score == 0.9

    def test_revenue_contracts(self):
        """Verifies FinancialParameters constraints, ProjectionScenario, and RevenueEstimationOutput."""
        params = FinancialParameters(
            monthly_price=10.0,
            starting_customers=100,
            monthly_growth_rate=0.15,
            monthly_churn_rate=0.03,
            cogs_per_unit=1.5,
            fixed_monthly_costs=500.0
        )
        scenario = ProjectionScenario(
            scenario_name="moderate",
            month_12_revenue=15000.0,
            month_12_customers=1500,
            break_even_month=6,
            monthly_projections=[{"month": 1, "revenue": 1000.0, "customers": 100}]
        )
        rev_output = RevenueEstimationOutput(
            pricing_strategy="Tiered B2C SaaS",
            parameters=params,
            scenarios=[scenario],
            tam_sam_som_valid=True,
            assumptions_summary=["5% conversion rate"]
        )
        assert rev_output.parameters.monthly_price == 10.0
        assert rev_output.scenarios[0].month_12_revenue == 15000.0

    def test_marketing_contracts(self):
        """Verifies Milestone and MarketingPlanOutput structure and budget allocations."""
        milestone = Milestone(
            month=1,
            week=1,
            focus="Beta launch",
            target_kpi="50 beta users",
            deliverables=["Landing page", "Feedback form"]
        )
        marketing = MarketingPlanOutput(
            positioning_statement="The all-in-one co-founder for student founders",
            priority_channels=["Social media", "Campus ambassadors"],
            messaging_framework={"headline": "Empower your journey"},
            gtm_90_day_plan=[milestone],
            acquisition_tactics=["Word of mouth"],
            budget_allocation={"social": 0.6, "events": 0.4},
            prioritized_next_actions=["Launch waitlist"]
        )
        assert len(marketing.gtm_90_day_plan) == 1
        assert marketing.gtm_90_day_plan[0].target_kpi == "50 beta users"

    def test_venture_state_full_lifecycle(self):
        """Verifies VentureState initialization, default stage, counters, and hydration."""
        founder = FounderInput(
            startup_idea="B2B Supply Chain Optimizer",
            target_market="Logistics",
            budget=200000.0
        )
        state = VentureState(
            venture_id="ven-12345",
            founder_input=founder,
            current_stage=WorkflowStage.INITIALIZED
        )
        assert state.current_stage == WorkflowStage.INITIALIZED
        assert state.replan_count == 0
        assert state.human_review_required is False
        assert state.venture_id == "ven-12345"
        assert state.founder_input.startup_idea == "B2B Supply Chain Optimizer"

        dumped = state.model_dump()
        restored = VentureState(**dumped)
        assert restored.venture_id == state.venture_id
        assert restored.current_stage == WorkflowStage.INITIALIZED
