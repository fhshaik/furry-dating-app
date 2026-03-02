"""Tests for backend/Dockerfile structure and best practices."""

import os
import re
import pytest

DOCKERFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "Dockerfile")


@pytest.fixture(scope="module")
def dockerfile_lines():
    with open(DOCKERFILE_PATH) as f:
        return f.read().splitlines()


@pytest.fixture(scope="module")
def dockerfile_text():
    with open(DOCKERFILE_PATH) as f:
        return f.read()


def test_dockerfile_exists():
    assert os.path.isfile(DOCKERFILE_PATH)


def test_multi_stage_build(dockerfile_text):
    """Dockerfile must have at least two FROM instructions (multi-stage build)."""
    from_lines = [l.strip() for l in dockerfile_text.splitlines() if l.strip().upper().startswith("FROM")]
    assert len(from_lines) >= 2, f"Expected multi-stage build (>=2 FROM), got: {from_lines}"


def test_builder_stage_uses_slim(dockerfile_text):
    """Builder stage should use python:3.12-slim for smaller image."""
    from_lines = [l.strip() for l in dockerfile_text.splitlines() if l.strip().upper().startswith("FROM")]
    builder_from = from_lines[0]
    assert "python:3.12-slim" in builder_from


def test_runtime_stage_uses_slim(dockerfile_text):
    """Runtime stage should use python:3.12-slim for smaller image."""
    from_lines = [l.strip() for l in dockerfile_text.splitlines() if l.strip().upper().startswith("FROM")]
    runtime_from = from_lines[1]
    assert "python:3.12-slim" in runtime_from


def test_copies_from_builder(dockerfile_text):
    """Runtime stage must copy compiled packages from builder stage."""
    assert "--from=builder" in dockerfile_text


def test_non_root_user_created(dockerfile_text):
    """Dockerfile must create a non-root user."""
    assert "useradd" in dockerfile_text or "adduser" in dockerfile_text


def test_non_root_user_switched(dockerfile_text):
    """Dockerfile must switch to non-root user with USER instruction."""
    user_lines = [l.strip() for l in dockerfile_text.splitlines() if l.strip().upper().startswith("USER")]
    assert user_lines, "No USER instruction found"
    # The final USER should not be root
    final_user = user_lines[-1]
    assert "root" not in final_user.lower(), f"Final USER must not be root, got: {final_user}"


def test_expose_8000(dockerfile_text):
    """Dockerfile must expose port 8000."""
    assert re.search(r"^EXPOSE\s+8000", dockerfile_text, re.MULTILINE)


def test_healthcheck_defined(dockerfile_text):
    """Dockerfile must define a HEALTHCHECK instruction."""
    assert re.search(r"^HEALTHCHECK", dockerfile_text, re.MULTILINE)


def test_healthcheck_has_interval(dockerfile_text):
    """HEALTHCHECK must specify an interval."""
    assert "--interval=" in dockerfile_text


def test_healthcheck_has_timeout(dockerfile_text):
    """HEALTHCHECK must specify a timeout."""
    assert "--timeout=" in dockerfile_text


def test_healthcheck_has_retries(dockerfile_text):
    """HEALTHCHECK must specify retries."""
    assert "--retries=" in dockerfile_text


def test_healthcheck_targets_health_endpoint(dockerfile_text):
    """HEALTHCHECK command should target the /health endpoint."""
    assert "/health" in dockerfile_text


def test_cmd_uses_uvicorn(dockerfile_text):
    """CMD must start the app with uvicorn."""
    assert "uvicorn" in dockerfile_text


def test_cmd_binds_all_interfaces(dockerfile_text):
    """uvicorn must bind to 0.0.0.0 so Docker can route traffic."""
    assert "0.0.0.0" in dockerfile_text


def test_no_cache_pip_install(dockerfile_text):
    """pip install must use --no-cache-dir to keep image lean."""
    assert "--no-cache-dir" in dockerfile_text


def test_requirements_copied_before_source(dockerfile_text):
    """requirements.txt should be copied before application source for layer caching."""
    lines = dockerfile_text.splitlines()
    req_idx = next((i for i, l in enumerate(lines) if "requirements.txt" in l and "COPY" in l), None)
    # COPY . . should come after requirements.txt copy
    app_copy_idx = next(
        (i for i, l in enumerate(lines) if re.search(r"^COPY\s+(--chown=\S+\s+)?\.(\s+\.)+", l)), None
    )
    assert req_idx is not None, "requirements.txt not copied"
    assert app_copy_idx is not None, "Application source not copied"
    assert req_idx < app_copy_idx, "requirements.txt should be copied before application source"
