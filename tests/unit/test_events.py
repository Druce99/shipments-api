import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.schemas.events import ShipmentStatusChanged


def make_event(**overrides: object) -> ShipmentStatusChanged:
    data: dict[str, object] = {
        "occurred_at": datetime(2026, 11, 5, 12, 0, tzinfo=UTC),
        "shipment_id": uuid.uuid4(),
        "tracking_number": "TRK-1",
        "old_status": ShipmentStatus.CREATED,
        "new_status": ShipmentStatus.PICKED_UP,
    }
    data.update(overrides)
    return ShipmentStatusChanged(**data)  # type: ignore[arg-type]


def test_event_id_is_generated_and_unique() -> None:
    assert make_event().event_id != make_event().event_id


def test_event_type_and_version_have_defaults() -> None:
    event = make_event()

    assert event.event_type == "shipment.status_changed"
    assert event.event_version == 1


def test_json_dump_contains_only_json_types() -> None:
    dump = make_event(comment="Courier took it").model_dump(mode="json")

    assert isinstance(dump["event_id"], str)
    assert isinstance(dump["shipment_id"], str)
    assert isinstance(dump["occurred_at"], str)
    assert dump["old_status"] == "created"
    assert dump["new_status"] == "picked_up"
    assert dump["comment"] == "Courier took it"


def test_event_can_be_restored_from_json_dump() -> None:
    original = make_event(comment="x")

    restored = ShipmentStatusChanged.model_validate(original.model_dump(mode="json"))

    assert restored == original


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_event(new_status="flying")
