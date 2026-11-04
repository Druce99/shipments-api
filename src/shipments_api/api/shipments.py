import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from shipments_api.api.dependencies import get_service
from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.schemas.shipment import (
    ShipmentCreate,
    ShipmentRead,
    StatusChange,
    StatusHistoryRead,
)
from shipments_api.service.shipment import ShipmentService

router = APIRouter(prefix="/shipments", tags=["shipments"])

ServiceDep = Annotated[ShipmentService, Depends(get_service)]


@router.post("", status_code=201)
async def create_shipment(data: ShipmentCreate, service: ServiceDep) -> ShipmentRead:
    shipment = await service.create_shipment(sender=data.sender, recipient=data.recipient)
    return ShipmentRead.model_validate(shipment)


@router.get("/{shipment_id}")
async def get_shipment(shipment_id: uuid.UUID, service: ServiceDep) -> ShipmentRead:
    shipment = await service.get_shipment(shipment_id)
    return ShipmentRead.model_validate(shipment)


@router.get("/{shipment_id}/history")
async def get_history(shipment_id: uuid.UUID, service: ServiceDep) -> list[StatusHistoryRead]:
    history = await service.get_history(shipment_id)
    return [StatusHistoryRead.model_validate(entry) for entry in history]


@router.get("")
async def list_shipments(
    service: ServiceDep,
    status: ShipmentStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ShipmentRead]:
    shipments = await service.list_shipments(status=status, limit=limit, offset=offset)
    return [ShipmentRead.model_validate(shipment) for shipment in shipments]


@router.patch("/{shipment_id}/status")
async def change_status(
    shipment_id: uuid.UUID, data: StatusChange, service: ServiceDep
) -> ShipmentRead:
    shipment = await service.change_status(
        shipment_id=shipment_id, new_status=data.status, comment=data.comment
    )
    return ShipmentRead.model_validate(shipment)
