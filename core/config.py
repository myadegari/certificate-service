"""Central configuration for the certificate service.

All settings are read once from the environment (and `.env` if present).
Every module must import `settings` from here instead of calling
`os.getenv` directly.
"""

from functools import lru_cache
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- RabbitMQ ---
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_vhost: str = "/"
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"
    rabbitmq_job_queue: str = "certificate_jobs"

    # --- Redis ---
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # --- MongoDB (shared with the Next.js app) ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "certification"

    # --- Object storage: Alarik (S3-compatible), shared with the app ---
    storage_endpoint: str = "http://127.0.0.1:8080"
    storage_region: str = "us-east-1"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    # Public base URL used to rewrite presigned URLs for browsers
    # (must match STORAGE_PUBLIC_URL in the Next.js app).
    storage_public_url: str = ""
    certificate_bucket: str = "certificate"

    # --- Status webhook back to the Next.js app ---
    # The worker POSTs certificate-job status here (HMAC-signed) so the app can
    # persist it and push to clients over SSE.
    next_webhook_url: str = ""
    webhook_secret: str = ""

    # --- PDF conversion ---
    # Path to the LibreOffice binary (soffice). Auto-detected when empty.
    libreoffice_path: str = ""

    # --- HTTP ---
    cors_allow_origins: str = "*"

    # --- Internal API ---
    # Shared secret required as the X-Internal-Token header on
    # /certificates/generate. Must match MICROSERVICE_TOKEN in the app.
    # When empty the endpoint is left open (local dev only).
    internal_api_token: str = ""

    # --- Working directories ---
    tmp_dir: str = "tmp"
    temp_certificates_dir: str = "temp_certificates"

    @property
    def amqp_url(self) -> str:
        # Credentials/vhost are percent-encoded: a password containing
        # @ : / # or the default "/" vhost would otherwise corrupt the URL.
        return (
            f"amqp://{quote(self.rabbitmq_user, safe='')}:{quote(self.rabbitmq_pass, safe='')}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{quote(self.rabbitmq_vhost or '/', safe='')}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{quote(self.redis_password, safe='')}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
