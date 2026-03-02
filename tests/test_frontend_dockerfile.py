"""Tests for frontend/Dockerfile structure and best practices."""

import os
import re
import pytest

DOCKERFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "Dockerfile")


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


def test_builder_stage_uses_node(dockerfile_text):
    """Builder stage should use a node image."""
    from_lines = [l.strip() for l in dockerfile_text.splitlines() if l.strip().upper().startswith("FROM")]
    builder_from = from_lines[0]
    assert "node:" in builder_from, f"Builder stage should use node image, got: {builder_from}"


def test_runtime_stage_uses_nginx(dockerfile_text):
    """Runtime stage should use an nginx image to serve static files."""
    from_lines = [l.strip() for l in dockerfile_text.splitlines() if l.strip().upper().startswith("FROM")]
    runtime_from = from_lines[-1]
    assert "nginx" in runtime_from, f"Runtime stage should use nginx image, got: {runtime_from}"


def test_copies_from_builder(dockerfile_text):
    """Runtime stage must copy built assets from builder stage."""
    assert "--from=builder" in dockerfile_text


def test_copies_dist_directory(dockerfile_text):
    """Runtime stage must copy the built dist/ output from builder."""
    assert "/app/dist" in dockerfile_text or "dist" in dockerfile_text


def test_package_json_copied_before_source(dockerfile_text):
    """package*.json should be copied before application source for layer caching."""
    lines = dockerfile_text.splitlines()
    pkg_idx = next((i for i, l in enumerate(lines) if "package" in l and "COPY" in l), None)
    app_copy_idx = next(
        (i for i, l in enumerate(lines) if re.search(r"^COPY\s+\.\s+\.", l.strip())), None
    )
    assert pkg_idx is not None, "package*.json not copied"
    assert app_copy_idx is not None, "Application source not copied"
    assert pkg_idx < app_copy_idx, "package*.json should be copied before application source"


def test_npm_install_runs(dockerfile_text):
    """Dockerfile must run npm install or npm ci to install dependencies."""
    assert re.search(r"npm\s+(ci|install)", dockerfile_text), "npm ci/install not found in Dockerfile"


def test_npm_build_runs(dockerfile_text):
    """Dockerfile must run npm run build to produce static assets."""
    assert re.search(r"npm\s+run\s+build", dockerfile_text), "npm run build not found in Dockerfile"


def test_expose_80(dockerfile_text):
    """Dockerfile must expose port 80 for nginx."""
    assert re.search(r"^EXPOSE\s+80", dockerfile_text, re.MULTILINE)


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


def test_cmd_starts_nginx(dockerfile_text):
    """CMD must start nginx."""
    assert "nginx" in dockerfile_text
    assert re.search(r'CMD\s+\[.*"nginx"', dockerfile_text)


def test_spa_routing_configured(dockerfile_text):
    """SPA routing must be configured — either inline or via a copied nginx.conf file."""
    has_inline = "try_files" in dockerfile_text and "index.html" in dockerfile_text
    has_external = re.search(r"COPY\s+nginx\.conf\s+/etc/nginx/conf\.d/", dockerfile_text) is not None
    assert has_inline or has_external, (
        "Dockerfile must configure SPA routing via try_files inline "
        "or by COPYing an nginx.conf file"
    )
