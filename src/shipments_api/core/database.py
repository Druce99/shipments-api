from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shipments_api.core.config import get_settings

engine = create_async_engine(get_settings().database_url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
