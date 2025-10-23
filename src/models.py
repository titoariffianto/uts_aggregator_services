from pydantic import BaseModel, Field
from datetime import datetime, timezone
datetime.now(timezone.utc)
from typing import Any, List, Union

class Event(BaseModel):
    topic: str
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "default_source"
    payload: dict


PublishPayload = Union[Event, List[Event]]