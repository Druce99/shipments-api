from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shipments_api.domain.exceptions import InvalidStatusTransition, ShipmentNotFound


async def shipment_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def invalid_transition_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ShipmentNotFound, shipment_not_found_handler)
    app.add_exception_handler(InvalidStatusTransition, invalid_transition_handler)
