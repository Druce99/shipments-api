import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.repository.outbox import OutboxRepository
from shipments_api.schemas.events import ShipmentStatusChanged


@pytest.fixture
def repository(session: AsyncSession) -> OutboxRepository:
    return OutboxRepository(session)


def make_event() -> ShipmentStatusChanged:
    return ShipmentStatusChanged(
        occurred_at=datetime(2026, 11, 5, 12, 0, tzinfo=UTC),
        shipment_id=uuid.uuid4(),
        tracking_number="TRK-1",
        old_status=ShipmentStatus.CREATED,
        new_status=ShipmentStatus.PICKED_UP,
    )


@pytest.mark.asyncio
async def test_get_unpublished_returns_empty_list_for_empty_table(
    repository: OutboxRepository,
) -> None:
    assert list(await repository.get_unpublished(limit=10)) == []


@pytest.mark.asyncio
async def test_get_unpublished_skips_published_and_keeps_id_order(
    repository: OutboxRepository,
) -> None:
    first = await repository.add(make_event())
    second = await repository.add(make_event())
    third = await repository.add(make_event())
    await repository.mark_published(second)

    result = await repository.get_unpublished(limit=10)

    assert [e.id for e in result] == [first.id, third.id]


@pytest.mark.asyncio
async def test_get_unpublished_respects_limit_and_returns_oldest(
    repository: OutboxRepository,
) -> None:
    first = await repository.add(make_event())
    await repository.add(make_event())

    result = await repository.get_unpublished(limit=1)

    assert [e.id for e in result] == [first.id]


@pytest.mark.asyncio
async def test_mark_published_sets_time_and_hides_event(
    repository: OutboxRepository,
) -> None:
    event = await repository.add(make_event())
    assert event.published_at is None

    await repository.mark_published(event)

    assert event.published_at is not None
    assert list(await repository.get_unpublished(limit=10)) == []
