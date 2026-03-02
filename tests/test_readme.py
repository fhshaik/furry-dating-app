"""Tests for README coverage of local setup, env vars, and deploy instructions."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
README_PATH = ROOT_DIR / "README.md"
ENV_EXAMPLE_PATH = ROOT_DIR / ".env.example"


def readme_text() -> str:
    return README_PATH.read_text()


def test_readme_exists():
    assert README_PATH.is_file()


def test_readme_has_requested_sections():
    content = readme_text()

    assert "## Local Development" in content
    assert "## Environment Variables" in content
    assert "## Deploy" in content


def test_readme_documents_local_dev_commands():
    content = readme_text()

    assert "cp .env.example .env" in content
    assert "docker compose -f docker-compose.local.yml up --build" in content
    assert "docker compose -f docker-compose.local.yml exec backend alembic upgrade head" in content


def test_readme_mentions_all_env_example_variables():
    content = readme_text()

    env_vars = [
        line.split("=", 1)[0]
        for line in ENV_EXAMPLE_PATH.read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    ]

    for env_var in env_vars:
        assert f"`{env_var}`" in content


def test_readme_mentions_optional_runtime_variables():
    content = readme_text()

    for env_var in (
        "API_RATE_LIMIT",
        "SENTRY_DSN",
        "SENTRY_TRACES_SAMPLE_RATE",
        "VITE_API_BASE_URL",
        "VITE_API_URL",
    ):
        assert f"`{env_var}`" in content


def test_readme_documents_production_deploy():
    content = readme_text()

    assert "docker compose -f docker-compose.prod.yml up --build -d" in content
    assert "docker compose -f docker-compose.prod.yml exec backend alembic upgrade head" in content
    assert "external database" in content
