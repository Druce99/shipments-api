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


@pytest.mark.asyncio
async def test_list_shipments_returns_empty_list_when_no_shipments(client: AsyncClient) -> None:
    response = await client.get("/shipments")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_shipments_returns_newest_first(client: AsyncClient) -> None:
    first = await client.post("/shipments", json={"sender": "Alice", "recipient": "Bob"})
    second = await client.post("/shipments", json={"sender": "Carol", "recipient": "Dan"})

    response = await client.get("/shipments")

    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == [second.json()["id"], first.json()["id"]]


@pytest.mark.asyncio
async def test_list_shipments_filters_by_status(client: AsyncClient) -> None:
    await client.post("/shipments", json={"sender": "Alice", "recipient": "Bob"})

    created = await client.get("/shipments", params={"status": "created"})
    delivered = await client.get("/shipments", params={"status": "delivered"})

    assert len(created.json()) == 1
    assert delivered.json() == []


@pytest.mark.asyncio
async def test_list_shipments_applies_limit_and_offset(client: AsyncClient) -> None:
    first = await client.post("/shipments", json={"sender": "Alice", "recipient": "Bob"})
    second = await client.post("/shipments", json={"sender": "Carol", "recipient": "Dan"})

    page_one = await client.get("/shipments", params={"limit": 1, "offset": 0})
    page_two = await client.get("/shipments", params={"limit": 1, "offset": 1})

    assert [s["id"] for s in page_one.json()] == [second.json()["id"]]
    assert [s["id"] for s in page_two.json()] == [first.json()["id"]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"status": "flying"}],
)
async def test_list_shipments_rejects_invalid_query_params(
    client: AsyncClient, params: dict[str, str | int]
) -> None:
    response = await client.get("/shipments", params=params)

    assert response.status_code == 422
