import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def _build_async_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return database_url

    pg_user = os.environ.get("POSTGRES_USER", "taskboard")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "taskboard")
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    pg_db = os.environ.get("POSTGRES_DB", "taskboard")
    return f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"


def _build_sync_database_url(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://", 1)


ASYNC_DATABASE_URL = _build_async_database_url()
SYNC_DATABASE_URL = _build_sync_database_url(ASYNC_DATABASE_URL)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-in-production-2026")

    # SQLAlchemy async / sync
    SQLALCHEMY_DATABASE_URI = ASYNC_DATABASE_URL
    SYNC_DATABASE_URI = SYNC_DATABASE_URL
    BACKUP_DIR = BACKUP_DIR

    # Flask-Smorest / OpenAPI
    API_TITLE = "TaskBoard API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_SWAGGER_UI_PATH = "/swagger-ui"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Redis / Session
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    SESSION_TYPE = "redis"
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "taskboard:"
    PERMANENT_SESSION_LIFETIME = timedelta(days=90)

    # Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=90)
    REMEMBER_COOKIE_SECURE = False        # set True in prod with HTTPS
    REMEMBER_COOKIE_HTTPONLY = True

    # CSRF
    WTF_CSRF_ENABLED = True

    # Backup schedule (disabled by default for Postgres deployments)
    DB_BACKUP_ENABLED = os.environ.get("DB_BACKUP_ENABLED", "false").lower() == "true"
    BACKUP_INTERVAL_HOURS = 6
    BACKUP_KEEP_COUNT = 20


class DevelopmentConfig(Config):
    DEBUG = True
    REMEMBER_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    REMEMBER_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
