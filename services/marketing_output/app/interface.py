"""Marketing Output Domain Strict Interface.

Exposes public entrypoints for Marketing / GTM Plan Generation and
final Startup Roadmap compilation.
All interactions from orchestrator or other agents must pass through this interface.
"""

from typing import List, Dict, Optional
from shared.contracts.idea import IdeaAnalysisOutput, FounderInput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.business_model import BusinessModelOutput
from shared.contracts.revenue import RevenueEstimationOutput
from shared.contracts.marketing import MarketingPlanOutput, Milestone
from shared.contracts.roadmap import ExecutionPhase, StartupRoadmap, VentureRisk
from shared.contracts.venture_state import VentureState

try:
    from services.marketing_output.app.agents.marketing.agent import MarketingAgent
except ImportError:
    from app.agents.marketing.agent import MarketingAgent



def run_marketing_plan(
    idea: IdeaAnalysisOutput,
    market: MarketResearchOutput,
    business_model: BusinessModelOutput,
    revenue: RevenueEstimationOutput,
    founder: Optional[FounderInput] = None
) -> MarketingPlanOutput:
    """Generates the GTM strategy, channel mix, positioning, and 90-day (12-week) execution plan."""
    agent = MarketingAgent()
    return agent.generate_plan(
        idea=idea,
        market=market,
        business_model=business_model,
        revenue=revenue,
        founder=founder
    )


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 2)


def _finance_confidence(revenue: RevenueEstimationOutput) -> float:
    score = 0.85 - (0.08 * len(revenue.invariant_violations or []))
    if revenue.unit_economics:
        if revenue.unit_economics.ltv_cac_ratio >= 3.0:
            score += 0.05
        else:
            score -= 0.10
    return _clamp_score(score)


def _composite_confidence(state: VentureState) -> float:
    components = [
        (state.idea_analysis.confidence_score if state.idea_analysis else None, 0.15),
        (state.market_research.confidence_score if state.market_research else None, 0.20),
        (state.business_model.confidence_score if state.business_model else None, 0.15),
        (state.market_validation.confidence_score if state.market_validation else None, 0.30),
        (_finance_confidence(state.revenue_estimation) if state.revenue_estimation else None, 0.20),
    ]
    available = [(score, weight) for score, weight in components if score is not None]
    total_weight = sum(weight for _, weight in available)
    if not available or total_weight == 0:
        return 0.5
    return _clamp_score(sum(score * weight for score, weight in available) / total_weight)


def _build_execution_phases(state: VentureState) -> List[ExecutionPhase]:
    milestones = state.marketing_plan.gtm_90_day_plan or []
    phase_specs = [
        (1, "Validation", 3, "Validate the problem, target customer, and willingness to pay before building.", (1, 3)),
        (2, "MVP", 3, "Build and ship the smallest sellable product that proves the core value proposition.", (4, 6)),
        (3, "Launch", 3, "Launch to the first cohort and establish repeatable acquisition channels.", (7, 9)),
        (4, "Scale", 3, "Scale the channels that work and operationalize delivery, retention, and finance.", (10, 12)),
    ]
    phases: List[ExecutionPhase] = []
    for number, name, duration, focus, (start_week, end_week) in phase_specs:
        window = [
            milestone
            for milestone in milestones
            if milestone.week is not None and start_week <= milestone.week <= end_week
        ]
        key_milestones = [milestone.focus for milestone in window][:3]
        success_metrics = [milestone.target_kpi for milestone in window][:3]
        if not key_milestones:
            key_milestones = [focus]
        if not success_metrics:
            success_metrics = ["Document evidence and decide whether to advance to the next phase."]
        phases.append(
            ExecutionPhase(
                phase_number=number,
                name=name,
                duration_weeks=duration,
                focus=focus,
                key_milestones=key_milestones,
                success_metrics=success_metrics,
            )
        )
    return phases


def _build_top_risks(state: VentureState) -> List[VentureRisk]:
    idea = state.idea_analysis
    market = state.market_research
    business_model = state.business_model
    revenue = state.revenue_estimation
    marketing = state.marketing_plan
    critic = state.market_validation

    candidates: List[VentureRisk] = []

    def add(category: str, risk: str, mitigation: str, likelihood: str = "MEDIUM", impact: str = "HIGH") -> None:
        if not risk or any(existing.risk == risk for existing in candidates):
            return
        candidates.append(
            VentureRisk(
                category=category,
                risk=risk,
                likelihood=likelihood,
                impact=impact,
                mitigation=mitigation,
            )
        )

    if critic and (critic.requires_pivot or critic.status.value != "VALID"):
        add(
            "Market",
            "Market validation is incomplete and demand may be weaker than forecast.",
            "Interview 20 target users, run a paid landing-page test, and secure five pre-commitments before scaling spend.",
            "HIGH",
            "HIGH",
        )
    elif market.entry_barriers:
        add(
            "Market",
            f"Market entry barrier: {market.entry_barriers[0]}",
            "Validate access with design partners and narrow the initial wedge to a segment where the barrier is lowest.",
        )
    else:
        add(
            "Market",
            "Demand may be lower than the forecast in the financial model.",
            "Run a paid landing-page test and secure five pre-commitments before increasing acquisition spend.",
        )

    if market.competitor_landscape:
        competitor_names = ", ".join(competitor.name for competitor in market.competitor_landscape[:3])
        add(
            "Competition",
            f"Existing competitors ({competitor_names}) can outspend or out-distribute the venture.",
            "Win a narrow customer wedge with a differentiated offer, proof points, and faster time-to-value than incumbents.",
        )
    else:
        add(
            "Competition",
            "A better-funded or better-distributed alternative may emerge.",
            "Track adjacent alternatives monthly and defend the wedge with proprietary workflow depth and customer proof.",
        )

    if idea.red_flags:
        add(
            "Product",
            idea.red_flags[0],
            "Resolve the highest-risk product assumption through a time-boxed prototype and five customer validation sessions.",
        )
    elif business_model.key_risks:
        mitigation = (
            business_model.mitigations[0]
            if business_model.mitigations
            else "Assign an owner, define a leading indicator, and review the risk weekly until it is reduced."
        )
        add("Product", business_model.key_risks[0], mitigation)
    else:
        add(
            "Product",
            "The product may not deliver enough value for customers to switch or pay.",
            "Ship a narrow MVP, instrument activation, and run five structured customer validation sessions.",
        )

    if revenue.invariant_violations:
        add(
            "Financial",
            revenue.invariant_violations[0],
            "Re-run the financial model with conservative pricing and churn assumptions before committing to paid acquisition.",
            "HIGH",
            "HIGH",
        )
    elif revenue.unit_economics and revenue.unit_economics.ltv_cac_ratio < 3.0:
        add(
            "Financial",
            "Unit economics may not support profitable paid acquisition.",
            "Hold CAC below the target and improve retention or pricing until LTV:CAC is at least 3:1.",
            "HIGH",
            "HIGH",
        )
    else:
        add(
            "Financial",
            "Revenue and cash-flow projections may miss plan.",
            "Track actual CAC, churn, and runway monthly and keep a conservative hiring and spend plan.",
        )

    compliance_terms = ("legal", "regulat", "compliance", "soc2", "soc 2", "gdpr", "hipaa", "privacy")
    compliance_constraint = next(
        (
            constraint
            for constraint in state.founder_input.constraints
            if any(term in constraint.lower() for term in compliance_terms)
        ),
        None,
    )
    if compliance_constraint:
        add(
            "Compliance",
            f"Regulatory or compliance obligation may delay launch: {compliance_constraint}",
            "Map the compliance requirements, budget for specialist review, and sequence the launch behind the minimum viable controls.",
        )
    elif marketing.warnings:
        add(
            "Execution",
            marketing.warnings[0],
            "Use the deterministic GTM plan as the baseline and assign a single owner to each acquisition experiment.",
        )
    else:
        add(
            "Execution",
            "Founder bandwidth and budget constraints may slow execution.",
            "Sequence one milestone at a time, define weekly leading indicators, and defer non-critical work until the validation gate is passed.",
        )

    fallback_risks = [
        (
            "Execution",
            "A key launch milestone may slip and delay first revenue.",
            "Set a weekly milestone review, identify the critical path, and cut scope before moving the launch date.",
        ),
        (
            "Retention",
            "Early customers may not adopt the product deeply enough to renew.",
            "Instrument activation and retention, onboard the first cohort manually, and run a 30-day value review with every account.",
        ),
        (
            "Talent",
            "The team may lack a critical skill needed to execute the roadmap.",
            "Document the capability gap and use contractors or advisors for the narrowest critical scope.",
        ),
    ]
    for category, risk, mitigation in fallback_risks:
        if len(candidates) >= 5:
            break
        add(category, risk, mitigation)

    return candidates[:5]


def run_roadmap_synthesis(state: VentureState) -> StartupRoadmap:
    """Synthesizes all completed domain outputs into the final unified StartupRoadmap."""
    if not (
        state.idea_analysis
        and state.market_research
        and state.business_model
        and state.revenue_estimation
        and state.marketing_plan
    ):
        raise ValueError("Cannot synthesize StartupRoadmap: All upstream domain stages must be completed.")

    idea = state.idea_analysis
    market = state.market_research
    revenue = state.revenue_estimation
    marketing = state.marketing_plan
    overall_confidence = _composite_confidence(state)
    execution_phases = _build_execution_phases(state)
    top_risks = _build_top_risks(state)

    idea_text = state.founder_input.startup_idea or "New Venture"
    venture_name = idea_text[:60].strip() or "New Venture"
    target_users = ", ".join(idea.target_users[:3]) if idea.target_users else "the target customer segment"
    som_text = f"${market.som_estimate:,.0f}" if market.som_estimate is not None else "an unquantified near-term market"

    moderate = next(
        (scenario for scenario in revenue.scenarios if scenario.scenario_name.lower() == "moderate"),
        revenue.scenarios[min(1, len(revenue.scenarios) - 1)] if revenue.scenarios else None,
    )
    projected_revenue = moderate.month_12_revenue if moderate else 0.0
    projected_arr = projected_revenue * 12

    executive_summary = (
        f"{venture_name} targets {target_users} with a near-term serviceable market estimated at {som_text}. "
        f"The moderate 12-month projection reaches ${projected_revenue:,.0f} in monthly revenue "
        f"(${projected_arr:,.0f} annualized) using the plan's {revenue.pricing_strategy.lower()} model. "
        f"The roadmap sequences validation, MVP delivery, launch, and scale across four gated phases, "
        f"with {len(top_risks)} cross-functional risks and explicit mitigations. "
        f"Overall confidence is {overall_confidence:.0%}; proceed only when each phase's success metrics are met."
    )

    return StartupRoadmap(
        venture_id=state.venture_id,
        venture_name=venture_name,
        founder_input=state.founder_input,
        idea_analysis=idea,
        market_research=market,
        business_model=state.business_model,
        revenue_estimation=revenue,
        marketing_plan=marketing,
        overall_confidence_score=overall_confidence,
        executive_summary=executive_summary,
        execution_phases=execution_phases,
        top_risks=top_risks,
    )
