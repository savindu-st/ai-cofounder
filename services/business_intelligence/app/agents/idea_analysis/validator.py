"""Input validation and sanitization for Idea Analysis domain."""

from typing import Tuple, List
from shared.contracts.idea import FounderInput


class IdeaValidationError(ValueError):
    """Raised when founder input fails basic viability or syntax checks."""
    pass


def validate_founder_input(founder_input: FounderInput) -> Tuple[FounderInput, List[str]]:
    """Validates and sanitizes raw founder input.
    
    Returns:
        Tuple containing sanitized FounderInput and a list of non-fatal advisory warnings.
    
    Raises:
        IdeaValidationError: If the input is fundamentally invalid or unprocessable.
    """
    warnings: List[str] = []

    # 1. Idea validation
    idea = (founder_input.startup_idea or "").strip()
    if not idea:
        raise IdeaValidationError("Startup idea cannot be empty.")
    if len(idea) < 15:
        raise IdeaValidationError(
            f"Startup idea description is too short ({len(idea)} chars). "
            "Please provide at least 15 characters describing the concept."
        )

    # 2. Target market validation
    market = (founder_input.target_market or "").strip()
    if not market:
        raise IdeaValidationError("Target market cannot be empty. Please specify your target audience or industry.")

    # 3. Budget sanitization
    budget = founder_input.budget
    if budget < 0.0:
        warnings.append(f"Negative budget provided (${budget:.2f}); clamped to $0.00.")
        budget = 0.0

    # 4. Timeline sanitization
    timeline = founder_input.timeline_months
    if timeline <= 0:
        warnings.append(f"Invalid timeline ({timeline} months); defaulting to 3 months.")
        timeline = 3
    elif timeline > 60:
        warnings.append(f"Long timeline ({timeline} months); clamped to 60 months (5 years) for planning horizons.")
        timeline = 60

    # 5. Geography normalization
    geography = (founder_input.target_geography or "").strip() or "Global"

    sanitized = FounderInput(
        startup_idea=idea,
        target_market=market,
        target_geography=geography,
        budget=budget,
        timeline_months=timeline,
        goals=(founder_input.goals or "").strip(),
        constraints=founder_input.constraints or [],
        skills_resources=(founder_input.skills_resources or "").strip() if founder_input.skills_resources else None
    )

    return sanitized, warnings
