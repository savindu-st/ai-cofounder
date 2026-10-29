"""Standalone responsive HTML renderer for a StartupRoadmap."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from shared.contracts.roadmap import StartupRoadmap

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _build_context(roadmap: StartupRoadmap) -> Dict[str, Any]:
    canvas = roadmap.business_model.canvas
    bmc_blocks: List[Dict[str, Any]] = [
        {"title": "Key Partners", "entries": canvas.key_partners},
        {"title": "Key Activities", "entries": canvas.key_activities},
        {"title": "Value Propositions", "entries": canvas.value_propositions},
        {"title": "Key Resources", "entries": canvas.key_resources},
        {"title": "Customer Relationships", "entries": canvas.customer_relationships},
        {"title": "Customer Segments", "entries": canvas.customer_segments},
        {"title": "Channels", "entries": canvas.channels},
        {"title": "Cost Structure", "entries": canvas.cost_structure},
        {"title": "Revenue Streams", "entries": canvas.revenue_streams},
    ]

    scenarios = roadmap.revenue_estimation.scenarios
    moderate = next(
        (scenario for scenario in scenarios if scenario.scenario_name.lower() == "moderate"),
        scenarios[min(1, len(scenarios) - 1)] if scenarios else None,
    )
    unit = roadmap.revenue_estimation.unit_economics
    summary_budget = sum((roadmap.marketing_plan.budget_allocation or {}).values())

    return {
        "roadmap": roadmap.model_dump(mode="json"),
        "bmc_blocks": bmc_blocks,
        "confidence_pct": round(roadmap.overall_confidence_score * 100),
        "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC"),
        "money": {
            "summary_budget": _money(summary_budget),
            "som": _money(roadmap.market_research.som_estimate),
            "moderate_arr": _money((moderate.month_12_revenue * 12) if moderate else 0),
            "unit_cac": _money(unit.cac if unit else 0),
            "unit_ltv": _money(unit.ltv if unit else 0),
            "scenarios": [_money(scenario.month_12_revenue) for scenario in scenarios],
        },
    }


def render_roadmap_html(roadmap: StartupRoadmap) -> str:
    """Render a complete standalone HTML document."""
    if not isinstance(roadmap, StartupRoadmap):
        raise TypeError("render_roadmap_html expects a StartupRoadmap instance")
    template = _ENV.get_template("roadmap_template.html")
    return template.render(**_build_context(roadmap))


def export_roadmap_html(roadmap: StartupRoadmap) -> str:
    """Backward-friendly alias for the HTML renderer."""
    return render_roadmap_html(roadmap)


render_html = render_roadmap_html
