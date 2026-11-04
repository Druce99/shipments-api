import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from shipments_api.api.dependencies import get_service
from shipments_api.schemas.shipment import ShipmentCreate, ShipmentRead, StatusHistoryRead
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
