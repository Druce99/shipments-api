import uuid
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
    response = await client.post(url="/shipments", json={"sender": "", "recipient": "Bob"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_shipment_returns_created_shipment(client: AsyncClient) -> None:
    created = await client.post("/shipments", json={"sender": "Alice", "recipient": "Bob"})
    shipment_id = created.json()["id"]

    response = await client.get(f"/shipments/{shipment_id}")

    assert response.status_code == 200
    assert response.json() == created.json()


@pytest.mark.asyncio
async def test_get_shipment_returns_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get(f"/shipments/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_shipment_returns_422_for_invalid_uuid(client: AsyncClient) -> None:
    response = await client.get("/shipments/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_history_returns_initial_entry(client: AsyncClient) -> None:
    created = await client.post("/shipments", json={"sender": "Alice", "recipient": "Bob"})
    shipment_id = created.json()["id"]

    response = await client.get(f"/shipments/{shipment_id}/history")

    assert response.status_code == 200
    body = response.json()
    assert [entry["status"] for entry in body] == ["created"]
    assert body[0]["comment"] is None


@pytest.mark.asyncio
async def test_get_history_returns_404_for_unknown_shipment(client: AsyncClient) -> None:
    response = await client.get(f"/shipments/{uuid.uuid4()}/history")

    assert response.status_code == 404
