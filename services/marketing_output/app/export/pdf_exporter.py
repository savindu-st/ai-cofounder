"""Executive PDF exporter built with ReportLab."""

from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Iterable, List, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from shared.contracts.roadmap import StartupRoadmap

_PAGE_WIDTH, _ = A4
_MARGIN = 15 * mm
_CONTENT_WIDTH = _PAGE_WIDTH - (2 * _MARGIN)
_FONT_NAME = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
try:
    _font_dir = os.path.join(os.path.dirname(__import__("reportlab").__file__), "fonts")
    pdfmetrics.registerFont(TTFont("RoadmapVera", os.path.join(_font_dir, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("RoadmapVera-Bold", os.path.join(_font_dir, "VeraBd.ttf")))
    _FONT_NAME = "RoadmapVera"
    _FONT_BOLD = "RoadmapVera-Bold"
except Exception:
    pass


def _text(value: Any) -> str:
    """Escape arbitrary model text for ReportLab's mini-HTML parser."""
    raw = "" if value is None else str(value)
    for source, replacement in (
        ("\u2018", "'"),
        ("\u2019", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u2013", "-"),
        ("\u2014", "-"),
        ("\u2026", "..."),
    ):
        raw = raw.replace(source, replacement)
    return html.escape(raw)


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _bullets(items: Iterable[Any]) -> str:
    values = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not values:
        return "<i>Not provided</i>"
    return "<br/>".join(f"&bull; {_text(item)}" for item in values)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "RoadmapTitle",
            parent=base["Title"],
            fontName=_FONT_BOLD,
            fontSize=28,
            leading=34,
            textColor=colors.HexColor("#172554"),
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "RoadmapSubtitle",
            parent=base["Normal"],
            fontName=_FONT_NAME,
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "RoadmapH1",
            parent=base["Heading1"],
            fontName=_FONT_BOLD,
            fontSize=18,
            leading=23,
            textColor=colors.HexColor("#1e3a8a"),
            spaceBefore=4,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "RoadmapH2",
            parent=base["Heading2"],
            fontName=_FONT_BOLD,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#312e81"),
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "RoadmapBody",
            parent=base["BodyText"],
            fontName=_FONT_NAME,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1f2937"),
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "RoadmapSmall",
            parent=base["BodyText"],
            fontName=_FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569"),
        ),
        "cell": ParagraphStyle(
            "RoadmapCell",
            parent=base["BodyText"],
            fontName=_FONT_NAME,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#1f2937"),
        ),
        "cell_title": ParagraphStyle(
            "RoadmapCellTitle",
            parent=base["BodyText"],
            fontName=_FONT_BOLD,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=3,
        ),
        "label": ParagraphStyle(
            "RoadmapLabel",
            parent=base["BodyText"],
            fontName=_FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
        ),
    }


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_text(value), style)


def _cell(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_text(value) if value is not None else "", style)


def _heading(value: Any, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(_text(value), styles["h1"])


def _table(data: Sequence[Sequence[Any]], widths: Sequence[float], *, header: bool = True) -> Table:
    table = Table(data, colWidths=list(widths), repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ]
    table.setStyle(TableStyle(commands))
    return table


def _page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
    canvas.line(_MARGIN, 12 * mm, _PAGE_WIDTH - _MARGIN, 12 * mm)
    canvas.setFont(_FONT_NAME, 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(_MARGIN, 8 * mm, "AI Co-Founder - Executive Startup Roadmap")
    canvas.drawRightString(_PAGE_WIDTH - _MARGIN, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _build_cover(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    founder = roadmap.founder_input
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
    story: List[Any] = [
        Spacer(1, 48 * mm),
        Paragraph("EXECUTIVE STARTUP ROADMAP", styles["subtitle"]),
        Spacer(1, 5 * mm),
        Paragraph(_text(roadmap.venture_name), styles["title"]),
        Spacer(1, 8 * mm),
        Paragraph(_text(roadmap.idea_analysis.refined_value_proposition), styles["subtitle"]),
        Spacer(1, 22 * mm),
    ]
    meta = [
        [Paragraph("Founder idea", styles["label"]), _p(founder.startup_idea, styles["body"])],
        [Paragraph("Target market", styles["label"]), _p(founder.target_market, styles["body"])],
        [Paragraph("Geography", styles["label"]), _p(founder.target_geography, styles["body"])],
        [Paragraph("Budget", styles["label"]), _p(_money(founder.budget), styles["body"])],
        [Paragraph("Timeline", styles["label"]), _p(f"{founder.timeline_months} months", styles["body"])],
        [Paragraph("Overall confidence", styles["label"]), _p(f"{roadmap.overall_confidence_score:.0%}", styles["body"])],
        [Paragraph("Generated", styles["label"]), _p(generated, styles["body"])],
    ]
    story.append(_table(meta, [42 * mm, 110 * mm], header=False))
    story.extend(
        [
            Spacer(1, 22 * mm),
            Paragraph(_text(roadmap.disclaimer), styles["small"]),
            PageBreak(),
        ]
    )
    return story


def _build_executive_summary(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    revenue = roadmap.revenue_estimation
    market = roadmap.market_research
    marketing = roadmap.marketing_plan
    story: List[Any] = [
        _heading("Executive Summary", styles),
        Paragraph(_text(roadmap.executive_summary), styles["body"]),
        Spacer(1, 3 * mm),
    ]
    snapshot = [
        ["Signal", "Snapshot"],
        ["Confidence", f"{roadmap.overall_confidence_score:.0%}"],
        ["TAM / SAM / SOM", f"{_money(market.tam_estimate)} / {_money(market.sam_estimate)} / {_money(market.som_estimate)}"],
        ["Pricing strategy", _text(revenue.pricing_strategy)],
        ["Priority channels", _text(", ".join(marketing.priority_channels) or "Founder-led outreach")],
        ["Archetype", _text(marketing.venture_archetype or "Not classified")],
        ["Budget allocated", _money(sum((marketing.budget_allocation or {}).values()))],
    ]
    story.append(_table(snapshot, [45 * mm, _CONTENT_WIDTH - 45 * mm]))
    if revenue.unit_economics:
        unit = revenue.unit_economics
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph("Unit Economics", styles["h2"]),
                _table(
                    [
                        ["ARPU", "Gross margin", "CAC", "LTV", "LTV:CAC", "CAC payback"],
                        [
                            _money(unit.arpu),
                            f"{unit.gross_margin:.1%}",
                            _money(unit.cac),
                            _money(unit.ltv),
                            f"{unit.ltv_cac_ratio:.1f}x",
                            f"{unit.cac_payback_months:.1f} mo",
                        ],
                    ],
                    [_CONTENT_WIDTH / 6] * 6,
                ),
            ]
        )
    story.append(PageBreak())
    return story


def _build_bmc(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    canvas = roadmap.business_model.canvas
    blocks = [
        ("Key Partners", canvas.key_partners),
        ("Key Activities", canvas.key_activities),
        ("Value Propositions", canvas.value_propositions),
        ("Key Resources", canvas.key_resources),
        ("Customer Relationships", canvas.customer_relationships),
        ("Customer Segments", canvas.customer_segments),
        ("Channels", canvas.channels),
        ("Cost Structure", canvas.cost_structure),
        ("Revenue Streams", canvas.revenue_streams),
    ]
    cell_width = _CONTENT_WIDTH / 3
    rows: List[List[Any]] = []
    for start in range(0, 9, 3):
        row = []
        for title, items in blocks[start:start + 3]:
            content = f"<b>{_text(title)}</b><br/>{_bullets(items)}"
            row.append(Paragraph(content, styles["cell"]))
        rows.append(row)
    return [
        _heading("Business Model Canvas", styles),
        _table(rows, [cell_width] * 3, header=False),
        Spacer(1, 5 * mm),
    ]


def _build_competitors(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    competitors = roadmap.market_research.competitor_landscape
    story: List[Any] = [_heading("Competitor Landscape", styles)]
    if not competitors:
        story.append(Paragraph("No direct competitors were identified in the research output.", styles["body"]))
        return story
    rows: List[List[Any]] = [["Competitor", "Description", "Strengths", "Weaknesses"]]
    for competitor in competitors[:8]:
        rows.append(
            [
                _cell(competitor.name, styles["cell_title"]),
                _cell(competitor.description, styles["cell"]),
                _cell(", ".join(competitor.strengths) or "-", styles["cell"]),
                _cell(", ".join(competitor.weaknesses) or "-", styles["cell"]),
            ]
        )
    story.append(_table(rows, [28 * mm, 55 * mm, 45 * mm, _CONTENT_WIDTH - 128 * mm]))
    sources = roadmap.market_research.source_urls
    if sources:
        story.extend(
            [
                Spacer(1, 3 * mm),
                Paragraph("Supporting Sources", styles["h2"]),
                Paragraph(_bullets(sources[:10]), styles["small"]),
            ]
        )
    story.append(Spacer(1, 5 * mm))
    return story


def _build_financials(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    revenue = roadmap.revenue_estimation
    story: List[Any] = [_heading("12-Month Financial Projections", styles)]
    rows: List[List[Any]] = [["Scenario", "Month 12 revenue", "Month 12 customers", "Break-even", "Ending runway"]]
    for scenario in revenue.scenarios:
        break_even = f"Month {scenario.break_even_month}" if scenario.break_even_month else "Not reached"
        runway = f"{scenario.ending_runway_months:.1f} mo" if scenario.ending_runway_months is not None else "-"
        rows.append(
            [
                _cell(scenario.scenario_name.title(), styles["cell_title"]),
                _cell(_money(scenario.month_12_revenue), styles["cell"]),
                _cell(f"{scenario.month_12_customers:,}", styles["cell"]),
                _cell(break_even, styles["cell"]),
                _cell(runway, styles["cell"]),
            ]
        )
    story.append(_table(rows, [32 * mm, 35 * mm, 35 * mm, 35 * mm, _CONTENT_WIDTH - 137 * mm]))
    params = revenue.parameters
    story.extend(
        [
            Spacer(1, 4 * mm),
            Paragraph("Model Assumptions", styles["h2"]),
            _table(
                [
                    ["Monthly price", "Starting customers", "Growth", "Churn", "COGS / unit", "Fixed costs"],
                    [
                        _money(params.monthly_price),
                        f"{params.starting_customers:,}",
                        f"{params.monthly_growth_rate:.1%}",
                        f"{params.monthly_churn_rate:.1%}",
                        _money(params.cogs_per_unit),
                        _money(params.fixed_monthly_costs),
                    ],
                ],
                [_CONTENT_WIDTH / 6] * 6,
            ),
        ]
    )
    if revenue.assumptions_summary:
        story.extend([Spacer(1, 3 * mm), Paragraph(_bullets(revenue.assumptions_summary[:8]), styles["body"])])
    if revenue.invariant_violations:
        story.extend(
            [
                Spacer(1, 3 * mm),
                Paragraph("Model Warnings", styles["h2"]),
                Paragraph(_bullets(revenue.invariant_violations), styles["small"]),
            ]
        )
    story.append(PageBreak())
    return story


def _build_phases(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    story: List[Any] = [_heading("Execution Roadmap", styles)]
    rows: List[List[Any]] = [["Phase", "Duration", "Focus", "Key milestones / success metrics"]]
    for phase in roadmap.execution_phases:
        milestones = "<br/>".join(f"&bull; {_text(item)}" for item in phase.key_milestones)
        metrics = "<br/>".join(f"&bull; {_text(item)}" for item in phase.success_metrics)
        details = f"{milestones}<br/><b>Success metrics</b><br/>{metrics}"
        rows.append(
            [
                _cell(f"{phase.phase_number}. {phase.name}", styles["cell_title"]),
                _cell(f"{phase.duration_weeks} weeks", styles["cell"]),
                _cell(phase.focus, styles["cell"]),
                Paragraph(details, styles["cell"]),
            ]
        )
    story.append(_table(rows, [30 * mm, 20 * mm, 55 * mm, _CONTENT_WIDTH - 105 * mm]))
    if roadmap.top_risks:
        story.extend([Spacer(1, 5 * mm), _heading("Top Cross-Functional Risks", styles)])
        risk_rows: List[List[Any]] = [["Category", "Risk", "Likelihood", "Impact", "Mitigation"]]
        for risk in roadmap.top_risks:
            risk_rows.append(
                [
                    _cell(risk.category, styles["cell_title"]),
                    _cell(risk.risk, styles["cell"]),
                    _cell(risk.likelihood, styles["cell"]),
                    _cell(risk.impact, styles["cell"]),
                    _cell(risk.mitigation, styles["cell"]),
                ]
            )
        story.append(_table(risk_rows, [24 * mm, 55 * mm, 20 * mm, 17 * mm, _CONTENT_WIDTH - 116 * mm]))
    story.append(PageBreak())
    return story


def _build_gtm_calendar(roadmap: StartupRoadmap, styles: dict[str, ParagraphStyle]) -> List[Any]:
    marketing = roadmap.marketing_plan
    story: List[Any] = [
        _heading("90-Day GTM Milestone Calendar", styles),
        Paragraph(_text(marketing.positioning_statement), styles["body"]),
        Spacer(1, 3 * mm),
    ]
    rows: List[List[Any]] = [["Week", "Focus", "Target KPI", "Deliverables"]]
    for milestone in marketing.gtm_90_day_plan:
        week = f"W{milestone.week}" if milestone.week else f"M{milestone.month}"
        rows.append(
            [
                _cell(week, styles["cell_title"]),
                _cell(milestone.focus, styles["cell"]),
                _cell(milestone.target_kpi, styles["cell"]),
                _cell("; ".join(milestone.deliverables) or "-", styles["cell"]),
            ]
        )
    story.append(_table(rows, [15 * mm, 52 * mm, 45 * mm, _CONTENT_WIDTH - 112 * mm]))
    if marketing.prioritized_next_actions:
        story.extend(
            [
                Spacer(1, 5 * mm),
                _heading("Prioritized Next Actions", styles),
                Paragraph(_bullets(marketing.prioritized_next_actions[:8]), styles["body"]),
            ]
        )
    return story


def generate_pdf(roadmap: StartupRoadmap) -> bytes:
    """Return a complete executive PDF as bytes."""
    if not isinstance(roadmap, StartupRoadmap):
        raise TypeError("generate_pdf expects a StartupRoadmap instance")

    styles = _styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=18 * mm,
        title=f"{roadmap.venture_name} - Executive Roadmap",
        author="AI Co-Founder",
        subject="Executive startup roadmap and business plan",
    )
    story: List[Any] = []
    story.extend(_build_cover(roadmap, styles))
    story.extend(_build_executive_summary(roadmap, styles))
    story.extend(_build_bmc(roadmap, styles))
    story.extend(_build_competitors(roadmap, styles))
    story.extend(_build_financials(roadmap, styles))
    story.extend(_build_phases(roadmap, styles))
    story.extend(_build_gtm_calendar(roadmap, styles))
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


def export_roadmap_pdf(roadmap: StartupRoadmap) -> bytes:
    """Backward-friendly alias for the PDF exporter."""
    return generate_pdf(roadmap)


generate_pdf_report = generate_pdf
