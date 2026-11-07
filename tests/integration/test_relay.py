import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.outbox import OutboxEvent
from shipments_api.relay.relay import OutboxRelay
from shipments_api.repository.outbox import OutboxRepository
from shipments_api.schemas.events import ShipmentStatusChanged


class FakePublisher:
    def __init__(self, fail_on_call: int | None = None) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self._fail_on_call = fail_on_call

    async def publish(self, key: str, value: dict[str, Any]) -> None:
        if self._fail_on_call == len(self.sent) + 1:
            raise RuntimeError("kafka is down")
        self.sent.append((key, value))


async def add_events(session: AsyncSession, count: int) -> list[OutboxEvent]:
    repository = OutboxRepository(session)
    events = []
    for _ in range(count):
        event = ShipmentStatusChanged(
            occurred_at=datetime(2026, 11, 5, 12, 0, tzinfo=UTC),
            shipment_id=uuid.uuid4(),
            tracking_number="TRK-1",
            old_status=ShipmentStatus.CREATED,
            new_status=ShipmentStatus.PICKED_UP,
        )
        events.append(await repository.add(event))
    # Close the transaction opened by add(): the relay starts its own ones.
    await session.commit()
    return events


async def read_all(session: AsyncSession) -> list[OutboxEvent]:
    session.expunge_all()
    result = await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id))
    return list(result.all())


def make_relay(
    session: AsyncSession, publisher: FakePublisher, batch_size: int = 100
) -> OutboxRelay:
    return OutboxRelay(session, OutboxRepository(session), publisher, batch_size)


@pytest.mark.asyncio
async def test_publish_pending_sends_all_events_in_order_and_marks_them(
    session: AsyncSession,
) -> None:
    events = await add_events(session, 3)
    expected_payloads = [e.payload for e in events]
    publisher = FakePublisher()

    count = await make_relay(session, publisher).publish_pending()

    assert count == 3
    assert [value for _, value in publisher.sent] == expected_payloads
    assert all(e.published_at is not None for e in await read_all(session))


@pytest.mark.asyncio
async def test_publish_pending_uses_shipment_id_as_key(session: AsyncSession) -> None:
    await add_events(session, 1)
    publisher = FakePublisher()

    await make_relay(session, publisher).publish_pending()

    key, value = publisher.sent[0]
    assert key == value["shipment_id"]


@pytest.mark.asyncio
async def test_publish_pending_does_nothing_when_there_are_no_events(
    session: AsyncSession,
) -> None:
    publisher = FakePublisher()

    count = await make_relay(session, publisher).publish_pending()

    assert count == 0
    assert publisher.sent == []


@pytest.mark.asyncio
async def test_publish_pending_respects_batch_size(session: AsyncSession) -> None:
    await add_events(session, 3)
    publisher = FakePublisher()

    count = await make_relay(session, publisher, batch_size=2).publish_pending()

    assert count == 2
    published = [e.published_at is not None for e in await read_all(session)]
    assert published == [True, True, False]


@pytest.mark.asyncio
async def test_publish_pending_keeps_already_sent_marked_when_publisher_fails(
    session: AsyncSession,
) -> None:
    await add_events(session, 3)
    publisher = FakePublisher(fail_on_call=2)

    with pytest.raises(RuntimeError):
        await make_relay(session, publisher).publish_pending()

    published = [e.published_at is not None for e in await read_all(session)]
    assert published == [True, False, False]
