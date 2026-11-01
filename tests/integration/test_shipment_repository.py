import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.shipment import Shipment, StatusHistory
from shipments_api.repository.shipment import ShipmentRepository


def make_shipment(
    tracking_number: str,
    status: ShipmentStatus = ShipmentStatus.CREATED,
    created_at: datetime | None = None,
) -> Shipment:
    shipment = Shipment(
        tracking_number=tracking_number,
        sender="Alice",
        recipient="Bob",
        current_status=status,
    )
    if created_at is not None:
        shipment.created_at = created_at
    return shipment


@pytest.mark.asyncio
async def test_add_then_get_returns_saved_shipment(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)
    tracking_number = "TRK-0001"
    shipment = make_shipment(tracking_number)
    await repo.add(shipment)
    shipment_id = shipment.id
    session.expunge_all()

    found = await repo.get(shipment_id)

    assert found is not None
    assert found is not shipment
    assert found.id == shipment_id
    assert found.tracking_number == tracking_number
    assert found.sender == "Alice"
    assert found.recipient == "Bob"
    assert found.current_status == ShipmentStatus.CREATED


@pytest.mark.asyncio
async def test_get_returns_none_for_unknown_id(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)

    found = await repo.get(uuid.uuid4())

    assert found is None


@pytest.mark.asyncio
async def test_get_for_update_returns_saved_shipment(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)
    shipment = make_shipment("TRK-0001")
    await repo.add(shipment)
    shipment_id = shipment.id
    session.expunge_all()

    found = await repo.get_for_update(shipment_id)

    assert found is not None
    assert found.id == shipment_id


@pytest.mark.asyncio
async def test_get_for_update_returns_none_for_unknown_id(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)

    found = await repo.get_for_update(uuid.uuid4())

    assert found is None


@pytest.mark.asyncio
async def test_list_history_returns_only_own_entries_in_insert_order(
    session: AsyncSession,
) -> None:
    repo = ShipmentRepository(session)
    first = make_shipment("TRK-0001")
    second = make_shipment("TRK-0002")
    await repo.add(first)
    await repo.add(second)
    first_id = first.id
    await repo.add_history(StatusHistory(shipment_id=first_id, status=ShipmentStatus.CREATED))
    await repo.add_history(
        StatusHistory(shipment_id=first_id, status=ShipmentStatus.PICKED_UP, comment="Courier")
    )
    await repo.add_history(StatusHistory(shipment_id=second.id, status=ShipmentStatus.CREATED))
    session.expunge_all()

    history = await repo.list_history(first_id)

    assert [entry.status for entry in history] == [
        ShipmentStatus.CREATED,
        ShipmentStatus.PICKED_UP,
    ]
    assert all(entry.shipment_id == first_id for entry in history)


@pytest.mark.asyncio
async def test_list_history_is_empty_for_shipment_without_history(
    session: AsyncSession,
) -> None:
    repo = ShipmentRepository(session)
    shipment = make_shipment("TRK-0001")
    await repo.add(shipment)

    history = await repo.list_history(shipment.id)

    assert list(history) == []


@pytest.mark.asyncio
async def test_list_shipments_without_filter_returns_all(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)
    for number in ("TRK-0001", "TRK-0002", "TRK-0003"):
        await repo.add(make_shipment(number))
    session.expunge_all()

    found = await repo.list_shipments(status=None, limit=10, offset=0)

    assert {s.tracking_number for s in found} == {"TRK-0001", "TRK-0002", "TRK-0003"}


@pytest.mark.asyncio
async def test_list_shipments_filters_by_status(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)
    await repo.add(make_shipment("TRK-0001", ShipmentStatus.CREATED))
    await repo.add(make_shipment("TRK-0002", ShipmentStatus.IN_TRANSIT))
    await repo.add(make_shipment("TRK-0003", ShipmentStatus.CREATED))
    session.expunge_all()

    found = await repo.list_shipments(status=ShipmentStatus.CREATED, limit=10, offset=0)

    assert {s.tracking_number for s in found} == {"TRK-0001", "TRK-0003"}


@pytest.mark.asyncio
async def test_list_shipments_returns_newest_first(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)
    await repo.add(make_shipment("TRK-0002", created_at=datetime(2026, 1, 2, tzinfo=UTC)))
    await repo.add(make_shipment("TRK-0003", created_at=datetime(2026, 1, 3, tzinfo=UTC)))
    await repo.add(make_shipment("TRK-0001", created_at=datetime(2026, 1, 1, tzinfo=UTC)))
    session.expunge_all()

    found = await repo.list_shipments(status=None, limit=10, offset=0)

    assert [s.tracking_number for s in found] == ["TRK-0003", "TRK-0002", "TRK-0001"]


@pytest.mark.asyncio
async def test_list_shipments_pages_do_not_overlap(session: AsyncSession) -> None:
    repo = ShipmentRepository(session)
    for number in ("TRK-0001", "TRK-0002", "TRK-0003"):
        await repo.add(make_shipment(number))
    session.expunge_all()

    first_page = await repo.list_shipments(status=None, limit=2, offset=0)
    second_page = await repo.list_shipments(status=None, limit=2, offset=2)

    assert len(first_page) == 2
    assert len(second_page) == 1
    all_ids = {s.id for s in [*first_page, *second_page]}
    assert len(all_ids) == 3
