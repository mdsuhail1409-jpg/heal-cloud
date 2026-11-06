"""
Unit Tests for Pydantic Settings and Application Configuration
"""

from app.core.config import Settings


def test_default_settings():
    """Verify default application settings are properly initialized."""
    config = Settings()
    assert config.PROJECT_NAME == "HealCloud"
    assert config.VERSION == "0.1.0"
    assert config.API_V1_STR == "/api/v1"
    assert config.LOG_LEVEL == "INFO"
    assert config.is_production is False


def test_cors_origins_parsing():
    """Verify CORS origins parses list and JSON string formats correctly."""
    # List format
    config_list = Settings(CORS_ORIGINS=["http://localhost:3000", "https://app.healcloud.io"])
    assert "http://localhost:3000" in config_list.CORS_ORIGINS
    assert "https://app.healcloud.io" in config_list.CORS_ORIGINS

    # JSON array string format
    config_json = Settings(CORS_ORIGINS='["http://localhost:5173", "https://staging.healcloud.io"]')
    assert len(config_json.CORS_ORIGINS) == 2
    assert "http://localhost:5173" in config_json.CORS_ORIGINS

    # Comma-separated string format
    config_csv = Settings(CORS_ORIGINS="http://localhost:8000, http://127.0.0.1:8000")
    assert len(config_csv.CORS_ORIGINS) == 2
    assert "http://localhost:8000" in config_csv.CORS_ORIGINS


def test_environment_helpers():
    """Verify environment detection helpers."""
    dev_config = Settings(ENVIRONMENT="development", DATABASE_URL="sqlite:///./dev.db")
    assert dev_config.is_production is False
    assert dev_config.is_sqlite is True

    prod_config = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+psycopg2://user:pass@db:5432/healcloud",
    )
    assert prod_config.is_production is True
    assert prod_config.is_sqlite is False

