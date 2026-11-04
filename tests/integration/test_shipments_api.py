from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.api.dependencies import get_session
from shipments_api.main import create_app


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_shipment_returns_201(client: AsyncClient) -> None:
    response = await client.post(url="/shipments", json={"sender": "Alice", "recipient": "Bob"})
    assert response.status_code == 201

    body = response.json()

    assert body["sender"] == "Alice"
    assert body["recipient"] == "Bob"
    assert body["current_status"] == "created"
    assert body["tracking_number"].startswith("TRK-")


@pytest.mark.asyncio
async def test_create_shipment_rejects_empty_sender(client: AsyncClient) -> None:
    response = await client.post(url="/shipments", json={"senser": "", "recipient": "Bob"})
    assert response.status_code == 422
