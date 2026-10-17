from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .statuses import ShipmentStatus


class DomainError(Exception):
    """Base class for all business-rule errors."""


class ShipmentNotFound(DomainError):
    def __init__(self, shipment_id: UUID) -> None:
        self.shipment_id = shipment_id
        super().__init__(f"Shipment {shipment_id} not found")


class InvalidStatusTransition(DomainError):
    def __init__(self, current: ShipmentStatus, target: ShipmentStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot change status from {current} to {target}")
