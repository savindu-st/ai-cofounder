from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class BaseContract(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore"
    )

class TimestampedContract(BaseContract):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

