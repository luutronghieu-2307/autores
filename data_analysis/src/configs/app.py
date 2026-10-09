from pydantic_settings import BaseSettings, SettingsConfigDict
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("/app/.env", ENV_PATH, ".env"), extra='ignore')

    KAFKA: str = ""
    OPEN_AI_KEY: str = ""

    GEMINI_KEY: str = ""
    MINIO_ENDPOINT: str = ""
    MINIO_PORT: int = 0
    MINIO_ACCESS_KEY_ID: str = ""
    MINIO_SECRET_ACCESS_KEY: str = ""
    MINIO_DOMAIN: str = ""
    MINIO_BUCKET_ANALYSIS: str = ""
    TMP_FOLDER: str = ""
    REDIS_STACK: str = ""
    REDIS_TTL: int = 0
    LOCALLLM_BASE_URL: str = ""
    API_KEY_ID: str = ""

settings = AppSettings()