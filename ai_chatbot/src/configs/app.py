from pydantic_settings import BaseSettings, SettingsConfigDict
import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

x = datetime.datetime.now()


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("/app/.env", ENV_PATH, ".env"), extra='ignore')

    KAFKA: str = ""
    OPEN_AI_KEY: str = ""

    GEMINI_KEY: str = ""

    REDIS_PWD: str = ""
    QDRANT_URL: str = ""
    REDIS_STACK: str = ""
    REDIS_HOST: str = ""
    REDIS_PORT: int = 0
    REDIS_TTL: int = 0
    EMBEDDING_MODEL: str = ""
    MINIO_ENDPOINT: str = ""
    MINIO_PORT: int = 0
    MINIO_ACCESS_KEY_ID: str = ""
    MINIO_SECRET_ACCESS_KEY: str = ""
    MINIO_DOMAIN: str = ""
    MINIO_PREFIX: str = ""
    TMP_FOLDER: str = ""
    MONGO_CONNECTION_STRING: str = ""
    LOCALLLM_BASE_URL: str = ""
    API_KEY_ID: str = ""


settings = AppSettings()