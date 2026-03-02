from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    api_rate_limit: str = "60/minute"
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0

    # OAuth — Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # OAuth — Discord
    discord_client_id: str = ""
    discord_client_secret: str = ""

    # JWT
    jwt_secret: str = "changeme"

    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "furconnect"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = "us-east-1"

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url]

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.sentry_dsn.strip())

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


settings = Settings()
