"""Deterministic Market Sizing Engine (TAM, SAM, SOM).

Combines top-down macroeconomic/industry estimates with bottom-up unit economics
(target customer counts * average annual contract value).
Enforces the fundamental economic invariant: 0 < SOM <= SAM <= TAM with automated
boundary correction and diagnostic logging.
"""

import logging
from typing import Tuple, List, Optional
from services.research.app.agents.market_research.schemas import MarketSizingSchema

logger = logging.getLogger(__name__)

# Default benchmark constants
DEFAULT_GLOBAL_TAM = 10_000_000_000.0  # $10B baseline software TAM
DEFAULT_GEOGRAPHY_FACTOR = 0.45         # North America / European early access
DEFAULT_SEGMENT_FACTOR = 0.30           # ICP segment focus
DEFAULT_SOM_PENETRATION = 0.05          # 5% realistic Year 1-2 obtainable market


class MarketSizingEngine:
    """Calculates and validates TAM, SAM, and SOM figures with dual methodology."""

    @staticmethod
    def validate_invariants(
        tam: Optional[float],
        sam: Optional[float],
        som: Optional[float]
    ) -> Tuple[bool, List[str]]:
        """Checks if TAM, SAM, and SOM satisfy 0 < SOM <= SAM <= TAM.

        Returns (is_valid, list_of_violations).
        """
        violations: List[str] = []

        if tam is None or tam <= 0:
            violations.append("TAM must be a positive number greater than 0.")
        if sam is None or sam <= 0:
            violations.append("SAM must be a positive number greater than 0.")
        if som is None or som <= 0:
            violations.append("SOM must be a positive number greater than 0.")

        if violations:
            return False, violations

        # Boundary checks
        if sam > tam:
            violations.append(f"SAM violation: SAM (${sam:,.2f}) cannot exceed TAM (${tam:,.2f}).")
        if som > sam:
            violations.append(f"SOM violation: SOM (${som:,.2f}) cannot exceed SAM (${sam:,.2f}).")

        return len(violations) == 0, violations

    @classmethod
    def auto_correct(
        cls,
        tam: Optional[float],
        sam: Optional[float],
        som: Optional[float]
    ) -> Tuple[float, float, float]:
        """Clamps and auto-corrects violated invariants to guarantee 0 < SOM <= SAM <= TAM."""
        # 1. Guarantee TAM floor
        clean_tam = float(tam) if (tam is not None and tam > 0) else DEFAULT_GLOBAL_TAM

        # 2. Guarantee SAM <= TAM
        if sam is None or sam <= 0:
            clean_sam = clean_tam * DEFAULT_GEOGRAPHY_FACTOR * DEFAULT_SEGMENT_FACTOR
        else:
            clean_sam = min(float(sam), clean_tam * 0.95)

        # 3. Guarantee SOM <= SAM
        if som is None or som <= 0:
            clean_som = clean_sam * DEFAULT_SOM_PENETRATION
        else:
            clean_som = min(float(som), clean_sam * 0.50)

        # Final absolute check
        if clean_som > clean_sam:
            clean_som = clean_sam * DEFAULT_SOM_PENETRATION
        if clean_sam > clean_tam:
            clean_sam = clean_tam * 0.50

        return clean_tam, clean_sam, clean_som

    @classmethod
    def triangulate(
        cls,
        top_down_tam: Optional[float] = None,
        estimated_target_customers: Optional[int] = None,
        annual_contract_value: Optional[float] = None,
        target_geography: str = "Global",
        cagr_pct: Optional[float] = 14.5,
        citations: Optional[List[str]] = None
    ) -> MarketSizingSchema:
        """Triangulates TAM, SAM, and SOM using top-down and bottom-up figures."""
        citations = citations or []
        methodology_parts = []

        # 1. Top-Down Calculation
        top_down = top_down_tam if (top_down_tam and top_down_tam > 0) else None
        if top_down:
            methodology_parts.append("top-down industry benchmarks")

        # 2. Bottom-Up Calculation: customers * ACV
        bottom_up = None
        if estimated_target_customers and estimated_target_customers > 0 and annual_contract_value and annual_contract_value > 0:
            bottom_up = float(estimated_target_customers) * float(annual_contract_value)
            methodology_parts.append("bottom-up customer account units * ACV")

        # 3. Triangulate TAM
        if top_down and bottom_up:
            # Average the two signals
            calculated_tam = (top_down + bottom_up) / 2.0
            methodology = "triangulated (top-down reports + bottom-up unit economics)"
        elif top_down:
            calculated_tam = top_down
            methodology = "top-down industry report estimate"
        elif bottom_up:
            calculated_tam = bottom_up
            methodology = "bottom-up account scaling estimate"
        else:
            calculated_tam = DEFAULT_GLOBAL_TAM
            methodology = "baseline sector heuristic"

        # 4. Determine Geographic & Segment Factor
        geo_lower = (target_geography or "global").lower()
        if "north america" in geo_lower or "us" in geo_lower or "usa" in geo_lower:
            geo_factor = 0.45
        elif "europe" in geo_lower or "eu" in geo_lower:
            geo_factor = 0.30
        elif "asia" in geo_lower:
            geo_factor = 0.35
        else:
            geo_factor = 0.50

        # SAM = TAM * geo_factor * segment_factor
        calculated_sam = calculated_tam * geo_factor * DEFAULT_SEGMENT_FACTOR

        # SOM = SAM * penetration (e.g. 5% in first 24 months)
        calculated_som = calculated_sam * DEFAULT_SOM_PENETRATION

        # Auto-correct and validate invariant
        final_tam, final_sam, final_som = cls.auto_correct(calculated_tam, calculated_sam, calculated_som)

        return MarketSizingSchema(
            tam=round(final_tam, 2),
            sam=round(final_sam, 2),
            som=round(final_som, 2),
            cagr_pct=cagr_pct,
            methodology=methodology,
            source_citations=citations
        )
