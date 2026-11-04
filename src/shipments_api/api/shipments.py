from typing import Annotated

from fastapi import APIRouter, Depends

from shipments_api.api.dependencies import get_service
from shipments_api.schemas.shipment import ShipmentCreate, ShipmentRead
from shipments_api.service.shipment import ShipmentService

router = APIRouter(prefix="/shipments", tags=["shipments"])

ServiceDep = Annotated[ShipmentService, Depends(get_service)]


@router.post("", status_code=201)
async def create_shipment(data: ShipmentCreate, service: ServiceDep) -> ShipmentRead:
    shipment = await service.create_shipment(sender=data.sender, recipient=data.recipient)
    return ShipmentRead.model_validate(shipment)
