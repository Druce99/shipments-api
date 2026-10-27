from sqlalchemy.orm import configure_mappers

import shipments_api.models.shipment  # noqa: F401


def test_mappers_configure_without_errors() -> None:
    configure_mappers()
