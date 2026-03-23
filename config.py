import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.environ.get("DB_PATH", "/Users/abhishek/Desktop/task_management/backups/tasks.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-in-production-2026")

    # SQLAlchemy async
    SQLALCHEMY_DATABASE_URI = f"sqlite+aiosqlite:///{DB_PATH}"
    DB_PATH = DB_PATH
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

    # Backup schedule (hours)
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
