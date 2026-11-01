from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import shipments_api.models.shipment  # noqa: F401
from shipments_api.models.base import Base
from tests.integration.settings import get_integration_settings


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    test_database_url = get_integration_settings().test_database_url

    db_name = make_url(test_database_url).database or ""
    if not db_name.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run: test database name must end with '_test', got {db_name!r}"
        )

    engine = create_async_engine(test_database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db_session:
            yield db_session
            await db_session.rollback()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
