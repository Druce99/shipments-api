from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.core.database import SessionFactory
from shipments_api.repository.shipment import ShipmentRepository
from shipments_api.service.shipment import ShipmentService


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


def get_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> ShipmentRepository:
    return ShipmentRepository(session)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    repository: Annotated[ShipmentRepository, Depends(get_repository)],
) -> ShipmentService:
    return ShipmentService(session, repository)
