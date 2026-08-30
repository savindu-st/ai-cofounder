from typing import List, Dict
from pydantic import Field
from shared.contracts.base import BaseContract

class Milestone(BaseContract):
    month: int
    focus: str
    target_kpi: str
    deliverables: List[str]

class MarketingPlanOutput(BaseContract):
    positioning_statement: str
    priority_channels: List[str]
    messaging_framework: Dict[str, str]
    gtm_90_day_plan: List[Milestone]
    acquisition_tactics: List[str]
    budget_allocation: Dict[str, float]
    prioritized_next_actions: List[str]
