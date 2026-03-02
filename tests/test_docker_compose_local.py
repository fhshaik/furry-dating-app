"""Tests for docker-compose.local.yml structure and correctness."""

import os
import yaml
import pytest

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.local.yml")


@pytest.fixture(scope="module")
def compose():
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)


def test_file_exists():
    assert os.path.isfile(COMPOSE_FILE)


def test_required_services(compose):
    services = compose["services"]
    assert set(services.keys()) == {"frontend", "backend", "mysql"}


def test_frontend_service(compose):
    svc = compose["services"]["frontend"]
    assert svc["build"]["context"] == "./frontend"
    assert svc["build"]["dockerfile"] == "Dockerfile"
    assert svc["build"]["target"] == "builder"
    assert svc["command"] == 'sh -c "npm ci && npm run dev -- --host 0.0.0.0 --port 5173"'
    assert svc["working_dir"] == "/app"
    assert "5173:5173" in svc["ports"]
    assert "backend" in svc["depends_on"]
    assert "./frontend:/app" in svc["volumes"]
    assert "/app/node_modules" in svc["volumes"]


def test_frontend_healthcheck(compose):
    hc = compose["services"]["frontend"]["healthcheck"]
    assert hc["test"] == ["CMD", "wget", "-qO-", "http://localhost:5173"]
    assert hc["interval"] == "10s"
    assert hc["timeout"] == "5s"
    assert hc["retries"] == 5


def test_backend_service(compose):
    svc = compose["services"]["backend"]
    assert svc["build"]["context"] == "./backend"
    assert svc["build"]["dockerfile"] == "Dockerfile"
    assert any("8000" in str(p) for p in svc["ports"])
    assert ".env" in svc["env_file"]
    # backend should connect to mysql service by hostname
    env = {e.split("=")[0]: e.split("=")[1] for e in svc["environment"]}
    assert env["MYSQL_HOST"] == "mysql"
    # backend depends on mysql
    assert "mysql" in svc["depends_on"]


def test_mysql_service(compose):
    svc = compose["services"]["mysql"]
    assert svc["image"].startswith("mysql:8")
    assert "ports" not in svc
    # named volume mounted
    volumes = svc.get("volumes", [])
    assert any("mysql_data" in str(v) for v in volumes)
    # healthcheck defined
    assert "healthcheck" in svc


def test_named_volume(compose):
    volumes = compose.get("volumes", {})
    assert "mysql_data" in volumes


def test_mysql_healthcheck_config(compose):
    hc = compose["services"]["mysql"]["healthcheck"]
    assert hc["interval"] == "10s"
    assert hc["timeout"] == "5s"
    assert hc["retries"] == 5
