"""Tests for docker-compose.prod.yml structure and correctness."""

import os
import yaml
import pytest

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.prod.yml")


@pytest.fixture(scope="module")
def compose():
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)


def test_file_exists():
    assert os.path.isfile(COMPOSE_FILE)


def test_required_services(compose):
    services = compose["services"]
    assert set(services.keys()) == {"frontend", "backend"}


def test_no_mysql_service(compose):
    """Prod uses external RDS — no local mysql service."""
    assert "mysql" not in compose["services"]


def test_no_named_volumes(compose):
    """Prod has no local DB volumes."""
    volumes = compose.get("volumes")
    assert not volumes


def test_frontend_service(compose):
    svc = compose["services"]["frontend"]
    assert svc["build"]["context"] == "./frontend"
    assert svc["build"]["dockerfile"] == "Dockerfile"
    assert any("80" in str(p) for p in svc["ports"])
    assert "backend" in svc["depends_on"]
    assert svc.get("restart") == "unless-stopped"


def test_frontend_no_dev_volumes(compose):
    """Production frontend should not mount source code."""
    svc = compose["services"]["frontend"]
    assert not svc.get("volumes"), "Prod frontend must not mount source volumes"


def test_backend_service(compose):
    svc = compose["services"]["backend"]
    assert svc["build"]["context"] == "./backend"
    assert svc["build"]["dockerfile"] == "Dockerfile"
    assert any("8000" in str(p) for p in svc["ports"])
    assert ".env" in svc["env_file"]
    assert svc.get("restart") == "unless-stopped"


def test_backend_no_dev_volumes(compose):
    """Production backend should not mount source code."""
    svc = compose["services"]["backend"]
    assert not svc.get("volumes"), "Prod backend must not mount source volumes"


def test_backend_environment_production(compose):
    svc = compose["services"]["backend"]
    env = svc.get("environment", [])
    env_dict = {e.split("=")[0]: e.split("=")[1] for e in env}
    assert env_dict.get("ENVIRONMENT") == "production"


def test_backend_requires_external_mysql_settings(compose):
    """Backend must fail fast unless external MySQL settings are provided."""
    svc = compose["services"]["backend"]
    env = svc.get("environment", [])
    env_dict = {e.split("=")[0]: e.split("=")[1] for e in env}
    assert env_dict["MYSQL_HOST"] == "${MYSQL_HOST:?MYSQL_HOST must be set for external MySQL}"
    assert env_dict["MYSQL_PORT"] == "${MYSQL_PORT:?MYSQL_PORT must be set for external MySQL}"
    assert env_dict["MYSQL_USER"] == "${MYSQL_USER:?MYSQL_USER must be set for external MySQL}"
    assert env_dict["MYSQL_PASSWORD"] == "${MYSQL_PASSWORD:?MYSQL_PASSWORD must be set for external MySQL}"
    assert env_dict["MYSQL_DATABASE"] == "${MYSQL_DATABASE:?MYSQL_DATABASE must be set for external MySQL}"


def test_backend_mysql_host_not_hardcoded_to_container_network(compose):
    """Production must not pin MySQL to an internal Docker hostname."""
    svc = compose["services"]["backend"]
    env = svc.get("environment", [])
    env_dict = {e.split("=")[0]: e.split("=")[1] for e in env}
    assert env_dict["MYSQL_HOST"] != "mysql"
    assert env_dict["MYSQL_HOST"] != "localhost"


def test_backend_no_depends_on_mysql(compose):
    """Backend must not depend on a local mysql service in prod."""
    svc = compose["services"]["backend"]
    depends = svc.get("depends_on", {})
    if isinstance(depends, list):
        assert "mysql" not in depends
    else:
        assert "mysql" not in depends
