import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from shipments_api.domain.statuses import ShipmentStatus


class ShipmentStatusChanged(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: Literal["shipment.status_changed"] = Field(default="shipment.status_changed")
    event_version: int = Field(default=1)
    occurred_at: datetime
    shipment_id: uuid.UUID
    tracking_number: str
    old_status: ShipmentStatus
    new_status: ShipmentStatus
    comment: str | None = None
