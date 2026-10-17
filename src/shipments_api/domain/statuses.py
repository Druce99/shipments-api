from collections.abc import Mapping
from enum import StrEnum

from .exceptions import InvalidStatusTransition


class ShipmentStatus(StrEnum):
    CREATED = "created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    FAILED_DELIVERY = "failed_delivery"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: Mapping[ShipmentStatus, frozenset[ShipmentStatus]] = {
    ShipmentStatus.CREATED: frozenset({ShipmentStatus.PICKED_UP, ShipmentStatus.CANCELLED}),
    ShipmentStatus.PICKED_UP: frozenset({ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED}),
    ShipmentStatus.IN_TRANSIT: frozenset(
        {ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.CANCELLED}
    ),
    ShipmentStatus.OUT_FOR_DELIVERY: frozenset(
        {ShipmentStatus.DELIVERED, ShipmentStatus.FAILED_DELIVERY}
    ),
    ShipmentStatus.FAILED_DELIVERY: frozenset(
        {ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.RETURNED}
    ),
    ShipmentStatus.DELIVERED: frozenset(),
    ShipmentStatus.RETURNED: frozenset(),
    ShipmentStatus.CANCELLED: frozenset(),
}


def validate_transition(current: ShipmentStatus, target: ShipmentStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(current, target)
