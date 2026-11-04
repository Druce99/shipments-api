from fastapi import FastAPI

from shipments_api.api.errors import register_exception_handlers
from shipments_api.api.shipments import router


def create_app() -> FastAPI:
    app = FastAPI(title="Shipments API")
    app.include_router(router)
    register_exception_handlers(app)
    return app


app = create_app()
