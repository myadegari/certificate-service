"""Central configuration for the certificate service.

All settings are read once from the environment (and `.env` if present).
Every module must import `settings` from here instead of calling
`os.getenv` directly.
"""

from functools import lru_cache

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
    rabbitmq_notification_queue: str = "certificate_notifications"

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
    report_bucket: str = "report"

    # --- PDF conversion ---
    # Path to the LibreOffice binary (soffice). Auto-detected when empty.
    libreoffice_path: str = ""

    # --- HTTP ---
    cors_allow_origins: str = "*"

    # --- Working directories ---
    tmp_dir: str = "tmp"
    temp_certificates_dir: str = "temp_certificates"
    temp_reports_dir: str = "temp_reports"

    @property
    def amqp_url(self) -> str:
        vhost = self.rabbitmq_vhost or "/"
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_pass}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
