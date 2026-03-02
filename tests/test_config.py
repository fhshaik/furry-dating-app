"""Tests for Settings (pydantic-settings config)."""


class TestSettingsDefaults:
    def test_default_environment(self):
        from app.core.config import Settings

        s = Settings()
        assert s.environment == "development"

    def test_default_frontend_url(self):
        from app.core.config import Settings

        s = Settings()
        assert s.frontend_url == "http://localhost:5173"

    def test_default_api_rate_limit(self):
        from app.core.config import Settings

        s = Settings()
        assert s.api_rate_limit == "60/minute"

    def test_default_sentry_dsn(self):
        from app.core.config import Settings

        s = Settings()
        assert s.sentry_dsn == ""

    def test_default_sentry_traces_sample_rate(self):
        from app.core.config import Settings

        s = Settings()
        assert s.sentry_traces_sample_rate == 0.0

    def test_default_mysql_host(self):
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_host == "localhost"

    def test_default_mysql_port(self):
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_port == 3306

    def test_default_mysql_user(self):
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_user == "root"

    def test_default_mysql_database(self):
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_database == "furconnect"

    def test_default_google_client_id(self):
        from app.core.config import Settings

        s = Settings()
        assert s.google_client_id == ""

    def test_default_google_client_secret(self):
        from app.core.config import Settings

        s = Settings()
        assert s.google_client_secret == ""

    def test_default_discord_client_id(self):
        from app.core.config import Settings

        s = Settings()
        assert s.discord_client_id == ""

    def test_default_discord_client_secret(self):
        from app.core.config import Settings

        s = Settings()
        assert s.discord_client_secret == ""

    def test_default_jwt_secret(self):
        from app.core.config import Settings

        s = Settings()
        assert s.jwt_secret == "changeme"

    def test_default_aws_access_key_id(self):
        from app.core.config import Settings

        s = Settings()
        assert s.aws_access_key_id == ""

    def test_default_aws_secret_access_key(self):
        from app.core.config import Settings

        s = Settings()
        assert s.aws_secret_access_key == ""

    def test_default_aws_s3_bucket(self):
        from app.core.config import Settings

        s = Settings()
        assert s.aws_s3_bucket == ""

    def test_default_aws_region(self):
        from app.core.config import Settings

        s = Settings()
        assert s.aws_region == "us-east-1"


class TestSettingsOverrides:
    def test_environment_override(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        from app.core.config import Settings

        s = Settings()
        assert s.environment == "production"

    def test_frontend_url_override(self, monkeypatch):
        monkeypatch.setenv("FRONTEND_URL", "https://example.com")
        from app.core.config import Settings

        s = Settings()
        assert s.frontend_url == "https://example.com"

    def test_api_rate_limit_override(self, monkeypatch):
        monkeypatch.setenv("API_RATE_LIMIT", "10/second")
        from app.core.config import Settings

        s = Settings()
        assert s.api_rate_limit == "10/second"

    def test_sentry_dsn_override(self, monkeypatch):
        monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
        from app.core.config import Settings

        s = Settings()
        assert s.sentry_dsn == "https://examplePublicKey@o0.ingest.sentry.io/0"

    def test_sentry_traces_sample_rate_override(self, monkeypatch):
        monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
        from app.core.config import Settings

        s = Settings()
        assert s.sentry_traces_sample_rate == 0.25

    def test_google_client_id_override(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-id-123")
        from app.core.config import Settings

        s = Settings()
        assert s.google_client_id == "google-id-123"

    def test_google_client_secret_override(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret-abc")
        from app.core.config import Settings

        s = Settings()
        assert s.google_client_secret == "google-secret-abc"

    def test_discord_client_id_override(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "discord-id-456")
        from app.core.config import Settings

        s = Settings()
        assert s.discord_client_id == "discord-id-456"

    def test_discord_client_secret_override(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "discord-secret-xyz")
        from app.core.config import Settings

        s = Settings()
        assert s.discord_client_secret == "discord-secret-xyz"

    def test_jwt_secret_override(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "supersecret")
        from app.core.config import Settings

        s = Settings()
        assert s.jwt_secret == "supersecret"

    def test_mysql_host_override(self, monkeypatch):
        monkeypatch.setenv("MYSQL_HOST", "db.example.com")
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_host == "db.example.com"

    def test_mysql_port_override(self, monkeypatch):
        monkeypatch.setenv("MYSQL_PORT", "3307")
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_port == 3307

    def test_mysql_user_override(self, monkeypatch):
        monkeypatch.setenv("MYSQL_USER", "furconnect_user")
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_user == "furconnect_user"

    def test_mysql_password_override(self, monkeypatch):
        monkeypatch.setenv("MYSQL_PASSWORD", "s3cr3t")
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_password == "s3cr3t"

    def test_mysql_database_override(self, monkeypatch):
        monkeypatch.setenv("MYSQL_DATABASE", "mydb")
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_database == "mydb"

    def test_aws_access_key_id_override(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        from app.core.config import Settings

        s = Settings()
        assert s.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"

    def test_aws_secret_access_key_override(self, monkeypatch):
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG")
        from app.core.config import Settings

        s = Settings()
        assert s.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG"

    def test_aws_s3_bucket_override(self, monkeypatch):
        monkeypatch.setenv("AWS_S3_BUCKET", "furconnect-images")
        from app.core.config import Settings

        s = Settings()
        assert s.aws_s3_bucket == "furconnect-images"

    def test_aws_region_override(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        from app.core.config import Settings

        s = Settings()
        assert s.aws_region == "eu-west-1"


class TestSettingsProperties:
    def test_cors_origins_includes_frontend_url(self):
        from app.core.config import Settings

        s = Settings()
        assert s.frontend_url in s.cors_origins

    def test_cors_origins_is_list(self):
        from app.core.config import Settings

        s = Settings()
        assert isinstance(s.cors_origins, list)

    def test_cors_origins_reflects_override(self, monkeypatch):
        monkeypatch.setenv("FRONTEND_URL", "https://app.furconnect.com")
        from app.core.config import Settings

        s = Settings()
        assert "https://app.furconnect.com" in s.cors_origins

    def test_database_url_format(self):
        from app.core.config import Settings

        s = Settings()
        url = s.database_url
        assert url.startswith("mysql+aiomysql://")

    def test_sentry_enabled_is_false_by_default(self):
        from app.core.config import Settings

        s = Settings()
        assert s.sentry_enabled is False

    def test_sentry_enabled_reflects_dsn(self, monkeypatch):
        monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
        from app.core.config import Settings

        s = Settings()
        assert s.sentry_enabled is True

    def test_database_url_contains_host(self):
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_host in s.database_url

    def test_database_url_contains_port(self):
        from app.core.config import Settings

        s = Settings()
        assert str(s.mysql_port) in s.database_url

    def test_database_url_contains_database_name(self):
        from app.core.config import Settings

        s = Settings()
        assert s.mysql_database in s.database_url

    def test_database_url_with_custom_values(self, monkeypatch):
        monkeypatch.setenv("MYSQL_HOST", "rds.example.com")
        monkeypatch.setenv("MYSQL_PORT", "3307")
        monkeypatch.setenv("MYSQL_USER", "admin")
        monkeypatch.setenv("MYSQL_PASSWORD", "pass")
        monkeypatch.setenv("MYSQL_DATABASE", "prod_db")
        from app.core.config import Settings

        s = Settings()
        assert s.database_url == "mysql+aiomysql://admin:pass@rds.example.com:3307/prod_db"


class TestSettingsSingleton:
    def test_settings_singleton_is_importable(self):
        from app.core.config import settings

        assert settings is not None

    def test_settings_singleton_has_expected_type(self):
        from app.core.config import Settings, settings

        assert isinstance(settings, Settings)
