import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.exceptions import InvalidStatusTransition, ShipmentNotFound
from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.outbox import OutboxEvent
from shipments_api.models.shipment import Shipment, StatusHistory
from shipments_api.repository.outbox import OutboxRepository
from shipments_api.repository.shipment import ShipmentRepository
from shipments_api.service.shipment import ShipmentService


@pytest.fixture
def service(session: AsyncSession) -> ShipmentService:
    return ShipmentService(session, ShipmentRepository(session), OutboxRepository(session))


async def create_shipment(
    session: AsyncSession, status: ShipmentStatus = ShipmentStatus.CREATED
) -> uuid.UUID:
    shipment = Shipment(
        tracking_number="TRK-0001",
        sender="Alice",
        recipient="Bob",
        current_status=status,
    )
    await ShipmentRepository(session).add(shipment)
    shipment_id = shipment.id
    # Close the transaction opened by add(): the service starts its own one.
    await session.commit()
    session.expunge_all()
    return shipment_id


async def read_state(
    session: AsyncSession, shipment_id: uuid.UUID
) -> tuple[ShipmentStatus, list[StatusHistory]]:
    session.expunge_all()
    repo = ShipmentRepository(session)
    shipment = await repo.get(shipment_id)
    assert shipment is not None
    history = await repo.list_history(shipment_id)
    return shipment.current_status, list(history)


@pytest.mark.asyncio
async def test_change_status_updates_status_and_writes_history(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    result = await service.change_status(shipment_id, ShipmentStatus.PICKED_UP, comment="Courier")

    assert result.current_status == ShipmentStatus.PICKED_UP
    status, history = await read_state(session, shipment_id)
    assert status == ShipmentStatus.PICKED_UP
    assert [(h.status, h.comment) for h in history] == [(ShipmentStatus.PICKED_UP, "Courier")]


@pytest.mark.asyncio
async def test_change_status_raises_not_found_for_unknown_shipment(
    service: ShipmentService,
) -> None:
    with pytest.raises(ShipmentNotFound):
        await service.change_status(uuid.uuid4(), ShipmentStatus.PICKED_UP)


@pytest.mark.asyncio
async def test_change_status_rejects_invalid_transition_and_keeps_data(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    with pytest.raises(InvalidStatusTransition):
        await service.change_status(shipment_id, ShipmentStatus.DELIVERED)

    status, history = await read_state(session, shipment_id)
    assert status == ShipmentStatus.CREATED
    assert history == []


@pytest.mark.asyncio
async def test_change_status_rolls_back_status_when_history_write_fails(
    session: AsyncSession,
    service: ShipmentService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shipment_id = await create_shipment(session)
    original_add_history = ShipmentRepository.add_history

    async def add_history_then_fail(self: ShipmentRepository, entry: StatusHistory) -> None:
        await original_add_history(self, entry)
        raise RuntimeError("boom")

    monkeypatch.setattr(ShipmentRepository, "add_history", add_history_then_fail)

    with pytest.raises(RuntimeError):
        await service.change_status(shipment_id, ShipmentStatus.PICKED_UP)

    status, history = await read_state(session, shipment_id)
    assert status == ShipmentStatus.CREATED
    assert history == []


@pytest.mark.asyncio
async def test_create_shipment_saves_shipment_with_initial_history(
    session: AsyncSession, service: ShipmentService
) -> None:
    created = await service.create_shipment(sender="Alice", recipient="Bob")
    shipment_id = created.id

    session.expunge_all()
    repo = ShipmentRepository(session)
    saved = await repo.get(shipment_id)
    history = await repo.list_history(shipment_id)
    assert saved is not None
    assert saved.tracking_number.startswith("TRK-")
    assert saved.sender == "Alice"
    assert saved.recipient == "Bob"
    assert saved.current_status == ShipmentStatus.CREATED
    assert [(h.status, h.comment) for h in history] == [(ShipmentStatus.CREATED, None)]


@pytest.mark.asyncio
async def test_create_shipment_rolls_back_shipment_when_history_write_fails(
    session: AsyncSession,
    service: ShipmentService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_add_history = ShipmentRepository.add_history

    async def add_history_then_fail(self: ShipmentRepository, entry: StatusHistory) -> None:
        await original_add_history(self, entry)
        raise RuntimeError("boom")

    monkeypatch.setattr(ShipmentRepository, "add_history", add_history_then_fail)

    with pytest.raises(RuntimeError):
        await service.create_shipment(sender="Alice", recipient="Bob")

    session.expunge_all()
    saved = await ShipmentRepository(session).list_shipments(status=None, limit=10, offset=0)
    assert list(saved) == []


@pytest.mark.asyncio
async def test_get_shipment_returns_existing_shipment(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    result = await service.get_shipment(shipment_id)

    assert result.id == shipment_id
    assert result.sender == "Alice"


@pytest.mark.asyncio
async def test_get_shipment_raises_not_found_for_unknown_shipment(
    service: ShipmentService,
) -> None:
    with pytest.raises(ShipmentNotFound):
        await service.get_shipment(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_history_returns_entries_in_order_of_writing(
    service: ShipmentService,
) -> None:
    created = await service.create_shipment(sender="Alice", recipient="Bob")
    await service.change_status(created.id, ShipmentStatus.PICKED_UP)
    await service.change_status(created.id, ShipmentStatus.IN_TRANSIT)

    history = await service.get_history(created.id)

    assert [h.status for h in history] == [
        ShipmentStatus.CREATED,
        ShipmentStatus.PICKED_UP,
        ShipmentStatus.IN_TRANSIT,
    ]


@pytest.mark.asyncio
async def test_get_history_raises_not_found_for_unknown_shipment(
    service: ShipmentService,
) -> None:
    with pytest.raises(ShipmentNotFound):
        await service.get_history(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_history_returns_empty_list_for_shipment_without_history(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    history = await service.get_history(shipment_id)

    assert list(history) == []


@pytest.mark.asyncio
async def test_list_shipments_filters_by_status(service: ShipmentService) -> None:
    await service.create_shipment(sender="Alice", recipient="Bob")
    picked_up = await service.create_shipment(sender="Carol", recipient="Dan")
    await service.change_status(picked_up.id, ShipmentStatus.PICKED_UP)

    result = await service.list_shipments(status=ShipmentStatus.PICKED_UP, limit=10, offset=0)

    assert [s.id for s in result] == [picked_up.id]


@pytest.mark.asyncio
async def test_list_shipments_without_status_returns_all(service: ShipmentService) -> None:
    await service.create_shipment(sender="Alice", recipient="Bob")
    await service.create_shipment(sender="Carol", recipient="Dan")

    result = await service.list_shipments(status=None, limit=10, offset=0)

    assert len(result) == 2


async def read_outbox(session: AsyncSession) -> list[OutboxEvent]:
    session.expunge_all()
    result = await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id))
    return list(result.all())


@pytest.mark.asyncio
async def test_change_status_writes_event_to_outbox(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    await service.change_status(shipment_id, ShipmentStatus.PICKED_UP, comment="Courier")

    events = await read_outbox(session)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "shipment.status_changed"
    assert event.published_at is None
    assert event.payload["event_id"] == str(event.event_id)
    assert event.payload["shipment_id"] == str(shipment_id)
    assert event.payload["old_status"] == "created"
    assert event.payload["new_status"] == "picked_up"
    assert event.payload["comment"] == "Courier"


@pytest.mark.asyncio
async def test_change_status_writes_one_event_per_change(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    await service.change_status(shipment_id, ShipmentStatus.PICKED_UP)
    await service.change_status(shipment_id, ShipmentStatus.IN_TRANSIT)

    events = await read_outbox(session)
    assert [(e.payload["old_status"], e.payload["new_status"]) for e in events] == [
        ("created", "picked_up"),
        ("picked_up", "in_transit"),
    ]


@pytest.mark.asyncio
async def test_change_status_writes_no_event_for_invalid_transition(
    session: AsyncSession, service: ShipmentService
) -> None:
    shipment_id = await create_shipment(session)

    with pytest.raises(InvalidStatusTransition):
        await service.change_status(shipment_id, ShipmentStatus.DELIVERED)

    assert await read_outbox(session) == []


@pytest.mark.asyncio
async def test_change_status_writes_no_event_for_unknown_shipment(
    session: AsyncSession, service: ShipmentService
) -> None:
    with pytest.raises(ShipmentNotFound):
        await service.change_status(uuid.uuid4(), ShipmentStatus.PICKED_UP)

    assert await read_outbox(session) == []


@pytest.mark.asyncio
async def test_change_status_rolls_back_everything_when_outbox_write_fails(
    session: AsyncSession,
    service: ShipmentService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shipment_id = await create_shipment(session)

    async def add_failing(self: OutboxRepository, event: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(OutboxRepository, "add", add_failing)

    with pytest.raises(RuntimeError):
        await service.change_status(shipment_id, ShipmentStatus.PICKED_UP)

    status, history = await read_state(session, shipment_id)
    assert status == ShipmentStatus.CREATED
    assert history == []
    assert await read_outbox(session) == []
