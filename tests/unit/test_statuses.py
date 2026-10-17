import pytest

from shipments_api.domain.exceptions import InvalidStatusTransition
from shipments_api.domain.statuses import ALLOWED_TRANSITIONS, ShipmentStatus, validate_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ShipmentStatus.CREATED, ShipmentStatus.PICKED_UP),
        (ShipmentStatus.CREATED, ShipmentStatus.CANCELLED),
        (ShipmentStatus.PICKED_UP, ShipmentStatus.IN_TRANSIT),
        (ShipmentStatus.PICKED_UP, ShipmentStatus.CANCELLED),
        (ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY),
        (ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED),
        (ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.DELIVERED),
        (ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.FAILED_DELIVERY),
        (ShipmentStatus.FAILED_DELIVERY, ShipmentStatus.OUT_FOR_DELIVERY),
        (ShipmentStatus.FAILED_DELIVERY, ShipmentStatus.RETURNED),
    ],
)
def test_allowed_transition_does_not_raise(current: ShipmentStatus, target: ShipmentStatus) -> None:
    validate_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ShipmentStatus.DELIVERED, ShipmentStatus.CREATED),
        (ShipmentStatus.CREATED, ShipmentStatus.DELIVERED),
        (ShipmentStatus.CREATED, ShipmentStatus.CREATED),
        (ShipmentStatus.CANCELLED, ShipmentStatus.PICKED_UP),
        (ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.CANCELLED),
        (ShipmentStatus.RETURNED, ShipmentStatus.OUT_FOR_DELIVERY),
    ],
)
def test_forbidden_transition_raises(current: ShipmentStatus, target: ShipmentStatus) -> None:
    with pytest.raises(InvalidStatusTransition) as exc_info:
        validate_transition(current, target)
    assert exc_info.value.current == current
    assert exc_info.value.target == target


@pytest.mark.parametrize(
    "terminal",
    [ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED, ShipmentStatus.CANCELLED],
)
@pytest.mark.parametrize("target", list(ShipmentStatus))
def test_terminal_status_has_no_transitions(
    terminal: ShipmentStatus, target: ShipmentStatus
) -> None:
    with pytest.raises(InvalidStatusTransition):
        validate_transition(terminal, target)


def test_every_status_has_entry_in_transition_table() -> None:
    assert set(ShipmentStatus) == set(ALLOWED_TRANSITIONS)
