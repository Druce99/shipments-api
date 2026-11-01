import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.exceptions import InvalidStatusTransition, ShipmentNotFound
from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.shipment import Shipment, StatusHistory
from shipments_api.repository.shipment import ShipmentRepository
from shipments_api.service.shipment import ShipmentService


@pytest.fixture
def service(session: AsyncSession) -> ShipmentService:
    return ShipmentService(session, ShipmentRepository(session))


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
