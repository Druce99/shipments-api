import pytest

from shipments_api.core.config import Settings


def test_settings_reads_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@localhost/testdb")
    settings = Settings()
    assert settings.database_url == "postgresql://fake:fake@localhost/testdb"
