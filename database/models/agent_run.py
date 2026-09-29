import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from shared.db.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    venture_id = Column(String, ForeignKey("ventures.id"), nullable=False, index=True)
    node_name = Column(String, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="SUCCESS")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    venture = relationship("Venture", back_populates="agent_runs")
