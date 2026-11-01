from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str


@lru_cache
def get_integration_settings() -> IntegrationSettings:
    return IntegrationSettings()
