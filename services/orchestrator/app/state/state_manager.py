"""State Manager for Venture Workflow.

Handles persistence of VentureState snapshots and agent telemetry to both
in-memory cache (for real-time access / testing) and PostgreSQL via SQLAlchemy.
"""

import logging
from typing import Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts.venture_state import VentureState
from database.models.venture import Venture
from database.models.venture_state import VentureStateRecord
from database.models.agent_run import AgentRun
from database.models.roadmap import RoadmapRecord

logger = logging.getLogger(__name__)

# Real-time in-memory store for active venture workflows
_IN_MEMORY_STATES: Dict[str, VentureState] = {}


async def save_venture_state(
    state: VentureState,
    session: Optional[AsyncSession] = None
) -> None:
    """Saves the current VentureState to memory and database (if session provided).
    
    Args:
        state: The current VentureState model instance.
        session: Optional SQLAlchemy AsyncSession for database persistence.
    """
    # 1. Update in-memory cache
    _IN_MEMORY_STATES[state.venture_id] = state

    # 2. Persist to DB if session is available
    if session is None:
        return

    try:
        # Check if venture exists; create if not
        stmt = select(Venture).where(Venture.id == state.venture_id)
        result = await session.execute(stmt)
        venture = result.scalars().first()

        title = state.idea_analysis.problem_statement[:100] if state.idea_analysis else f"Venture {state.venture_id}"
        if not venture:
            venture = Venture(
                id=state.venture_id,
                title=title,
                status=state.current_stage.value,
            )
            session.add(venture)
        else:
            venture.status = state.current_stage.value
            if state.idea_analysis:
                venture.title = title

        # Append state history record
        state_record = VentureStateRecord(
            venture_id=state.venture_id,
            stage=state.current_stage.value,
            state_json=state.model_dump(mode="json"),
        )
        session.add(state_record)

        # Upsert final roadmap if synthesized
        if state.final_roadmap:
            roadmap_stmt = select(RoadmapRecord).where(RoadmapRecord.venture_id == state.venture_id)
            roadmap_result = await session.execute(roadmap_stmt)
            roadmap_rec = roadmap_result.scalars().first()
            if not roadmap_rec:
                roadmap_rec = RoadmapRecord(
                    venture_id=state.venture_id,
                    roadmap_json=state.final_roadmap.model_dump(mode="json"),
                    confidence_score=state.final_roadmap.overall_confidence_score,
                )
                session.add(roadmap_rec)
            else:
                roadmap_rec.roadmap_json = state.final_roadmap.model_dump(mode="json")
                roadmap_rec.confidence_score = state.final_roadmap.overall_confidence_score

        await session.commit()
    except Exception as e:
        logger.warning(f"Failed to persist state to database for venture {state.venture_id}: {e}")
        await session.rollback()


async def get_venture_state(
    venture_id: str,
    session: Optional[AsyncSession] = None
) -> Optional[VentureState]:
    """Retrieves the latest VentureState from in-memory cache or database.
    
    Args:
        venture_id: Unique venture ID.
        session: Optional SQLAlchemy AsyncSession.
        
    Returns:
        VentureState instance if found, otherwise None.
    """
    # Check in-memory cache first
    if venture_id in _IN_MEMORY_STATES:
        return _IN_MEMORY_STATES[venture_id]

    # Query DB if session provided
    if session is not None:
        try:
            stmt = (
                select(VentureStateRecord)
                .where(VentureStateRecord.venture_id == venture_id)
                .order_by(VentureStateRecord.id.desc())
            )
            result = await session.execute(stmt)
            latest_record = result.scalars().first()
            if latest_record and latest_record.state_json:
                state = VentureState.model_validate(latest_record.state_json)
                _IN_MEMORY_STATES[venture_id] = state
                return state
        except Exception as e:
            logger.warning(f"Failed to load state from database for venture {venture_id}: {e}")

    return None


async def record_agent_run(
    venture_id: str,
    node_name: str,
    duration_ms: Optional[int] = None,
    tokens: Optional[int] = None,
    cost: Optional[float] = None,
    status: str = "SUCCESS",
    session: Optional[AsyncSession] = None
) -> None:
    """Logs an agent run telemetry event in the database."""
    if session is None:
        return

    try:
        run = AgentRun(
            venture_id=venture_id,
            node_name=node_name,
            duration_ms=duration_ms,
            tokens=tokens,
            cost=cost,
            status=status,
        )
        session.add(run)
        await session.commit()
    except Exception as e:
        logger.warning(f"Failed to log agent run for {venture_id}/{node_name}: {e}")
        await session.rollback()
