import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from shared.db.base import Base


class Venture(Base):
    __tablename__ = "ventures"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="IN_PROGRESS")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="ventures")
    states = relationship("VentureStateRecord", back_populates="venture", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="venture", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="venture", cascade="all, delete-orphan")
    roadmap = relationship("RoadmapRecord", back_populates="venture", uselist=False, cascade="all, delete-orphan")
