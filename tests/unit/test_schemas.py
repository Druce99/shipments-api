import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.shipment import Shipment, StatusHistory
from shipments_api.schemas.shipment import (
    ShipmentCreate,
    ShipmentRead,
    StatusChange,
    StatusHistoryRead,
)


def test_shipment_create_strips_whitespace() -> None:
    data = ShipmentCreate(sender="  Alice  ", recipient=" Bob ")

    assert data.sender == "Alice"
    assert data.recipient == "Bob"


def test_shipment_create_accepts_max_length() -> None:
    data = ShipmentCreate(sender="x" * 200, recipient="y" * 200)

    assert len(data.sender) == 200
    assert len(data.recipient) == 200


@pytest.mark.parametrize("field", ["sender", "recipient"])
@pytest.mark.parametrize("value", ["", "   ", "x" * 201])
def test_shipment_create_rejects_invalid_value(field: str, value: str) -> None:
    payload = {"sender": "Alice", "recipient": "Bob"}
    payload[field] = value

    with pytest.raises(ValidationError):
        ShipmentCreate.model_validate(payload)


@pytest.mark.parametrize("missing", ["sender", "recipient"])
def test_shipment_create_requires_both_fields(missing: str) -> None:
    payload = {"sender": "Alice", "recipient": "Bob"}
    del payload[missing]

    with pytest.raises(ValidationError):
        ShipmentCreate.model_validate(payload)


def test_shipment_create_ignores_fields_client_must_not_set() -> None:
    payload = {
        "sender": "Alice",
        "recipient": "Bob",
        "current_status": "delivered",
        "tracking_number": "TRK-HACKED",
    }

    data = ShipmentCreate.model_validate(payload)

    assert not hasattr(data, "current_status")
    assert not hasattr(data, "tracking_number")


def test_shipment_read_is_built_from_orm_object() -> None:
    shipment_id = uuid.uuid4()
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    shipment = Shipment(
        id=shipment_id,
        tracking_number="TRK-0001",
        sender="Alice",
        recipient="Bob",
        current_status=ShipmentStatus.CREATED,
        created_at=moment,
        updated_at=moment,
    )

    result = ShipmentRead.model_validate(shipment)

    assert result.id == shipment_id
    assert result.tracking_number == "TRK-0001"
    assert result.current_status == ShipmentStatus.CREATED
    assert result.created_at == moment


def test_shipment_read_serializes_to_json_friendly_values() -> None:
    shipment_id = uuid.uuid4()
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    result = ShipmentRead(
        id=shipment_id,
        tracking_number="TRK-0001",
        sender="Alice",
        recipient="Bob",
        current_status=ShipmentStatus.CREATED,
        created_at=moment,
        updated_at=moment,
    )

    dumped = result.model_dump(mode="json")

    assert dumped["id"] == str(shipment_id)
    assert dumped["current_status"] == "created"


def test_status_change_accepts_status_string_and_defaults_comment_to_none() -> None:
    data = StatusChange.model_validate({"status": "picked_up"})

    assert data.status == ShipmentStatus.PICKED_UP
    assert data.comment is None


def test_status_change_strips_comment() -> None:
    data = StatusChange(status=ShipmentStatus.PICKED_UP, comment="  Courier took it  ")

    assert data.comment == "Courier took it"


def test_status_change_accepts_max_comment_length() -> None:
    data = StatusChange(status=ShipmentStatus.PICKED_UP, comment="x" * 500)

    assert data.comment is not None
    assert len(data.comment) == 500


@pytest.mark.parametrize("status", ["flying", "", "PICKED_UP"])
def test_status_change_rejects_unknown_status(status: str) -> None:
    with pytest.raises(ValidationError):
        StatusChange.model_validate({"status": status})


def test_status_change_requires_status() -> None:
    with pytest.raises(ValidationError):
        StatusChange.model_validate({"comment": "no status"})


@pytest.mark.parametrize("comment", ["", "   ", "x" * 501])
def test_status_change_rejects_invalid_comment(comment: str) -> None:
    with pytest.raises(ValidationError):
        StatusChange.model_validate({"status": "picked_up", "comment": comment})


def test_status_history_read_is_built_from_orm_object() -> None:
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    entry = StatusHistory(
        id=7,
        shipment_id=None,
        status=ShipmentStatus.PICKED_UP,
        comment="Courier",
        created_at=moment,
    )

    result = StatusHistoryRead.model_validate(entry)

    assert result.id == 7
    assert result.status == ShipmentStatus.PICKED_UP
    assert result.comment == "Courier"
    assert result.created_at == moment
