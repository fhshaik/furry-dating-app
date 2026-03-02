"""Tests for frontend/nginx.conf — SPA fallback routing and /api proxy pass."""

import os
import re
import pytest

NGINX_CONF_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "nginx.conf")
DOCKERFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "Dockerfile")


@pytest.fixture(scope="module")
def nginx_conf():
    with open(NGINX_CONF_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def dockerfile_text():
    with open(DOCKERFILE_PATH) as f:
        return f.read()


def _extract_location_block(nginx_conf: str, location: str) -> str:
    match = re.search(
        rf"location\s+{re.escape(location)}\s*\{{(?P<body>[^}}]*)\}}",
        nginx_conf,
        re.DOTALL,
    )
    assert match, f"location {location} block must exist"
    return match.group("body")


def _select_location(path: str) -> str:
    if path.startswith("/api/"):
        return "/api/"
    if path.startswith("/ws/"):
        return "/ws/"
    if path == "/health":
        return "/health"
    return "/"


def _resolve_root_try_files(path: str, existing_paths: set[str]) -> str:
    if path in existing_paths:
        return path
    if f"{path}/" in existing_paths:
        return f"{path}/"
    return "/index.html"


# --- nginx.conf existence and structure ---

def test_nginx_conf_exists():
    assert os.path.isfile(NGINX_CONF_PATH), "frontend/nginx.conf must exist"


def test_listens_on_port_80(nginx_conf):
    assert re.search(r"listen\s+80;", nginx_conf), "nginx must listen on port 80"


def test_root_points_to_html_dir(nginx_conf):
    assert re.search(r"root\s+/usr/share/nginx/html;", nginx_conf), \
        "root must point to /usr/share/nginx/html"


def test_index_html(nginx_conf):
    assert re.search(r"index\s+index\.html;", nginx_conf), \
        "index directive must include index.html"


# --- SPA fallback routing ---

def test_spa_try_files_directive(nginx_conf):
    assert "try_files" in nginx_conf, "try_files directive required for SPA routing"


def test_spa_fallback_to_index_html(nginx_conf):
    assert re.search(r"try_files\s+\$uri\s+\$uri/\s+/index\.html;", nginx_conf), \
        "try_files must fall back to /index.html for SPA client-side routing"


def test_spa_location_block(nginx_conf):
    """Root location block must exist with SPA try_files."""
    assert re.search(r"location\s+/\s*\{[^}]*try_files", nginx_conf, re.DOTALL), \
        "location / block must contain try_files for SPA routing"


@pytest.mark.parametrize(
    "client_route",
    [
        "/discover",
        "/matches",
        "/notifications",
        "/inbox",
        "/inbox/123",
        "/packs",
        "/my-packs",
        "/packs/new",
        "/packs/42",
        "/packs/42/edit",
        "/profile/edit",
        "/fursonas",
        "/auth/callback",
        "/login",
    ],
)
def test_client_side_routes_fall_back_to_index_html(nginx_conf, client_route):
    """Known React Router URLs should resolve through the SPA fallback."""
    root_block = _extract_location_block(nginx_conf, "/")

    assert _select_location(client_route) == "/"
    assert "try_files $uri $uri/ /index.html;" in root_block
    assert _resolve_root_try_files(client_route, existing_paths={"/assets/app.js"}) == "/index.html"


@pytest.mark.parametrize(
    ("path", "expected_location"),
    [
        ("/api/users/me", "/api/"),
        ("/ws/chat", "/ws/"),
        ("/health", "/health"),
    ],
)
def test_reserved_prefixes_do_not_use_spa_fallback(path, expected_location):
    assert _select_location(path) == expected_location


def test_existing_static_assets_do_not_fall_back_to_index_html():
    existing_paths = {"/assets/index-abc123.js", "/images", "/images/"}

    assert _resolve_root_try_files("/assets/index-abc123.js", existing_paths) == "/assets/index-abc123.js"
    assert _resolve_root_try_files("/images", existing_paths) == "/images"


# --- /api proxy pass ---

def test_api_location_block_exists(nginx_conf):
    assert re.search(r"location\s+/api/?\s*\{", nginx_conf), \
        "location /api/ block must exist to proxy backend requests"


def test_api_proxy_pass(nginx_conf):
    assert re.search(r"proxy_pass\s+http://backend:8000", nginx_conf), \
        "proxy_pass must target http://backend:8000"


def test_api_proxy_http_version(nginx_conf):
    assert re.search(r"proxy_http_version\s+1\.1;", nginx_conf), \
        "proxy_http_version 1.1 required for proper proxying"


def test_api_proxy_host_header(nginx_conf):
    assert re.search(r"proxy_set_header\s+Host\s+\$host;", nginx_conf), \
        "proxy_set_header Host must forward the Host header"


def test_api_proxy_x_real_ip(nginx_conf):
    assert re.search(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr;", nginx_conf), \
        "X-Real-IP header must be forwarded for correct client IP logging"


def test_api_proxy_x_forwarded_for(nginx_conf):
    assert re.search(r"proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for;", nginx_conf), \
        "X-Forwarded-For header must be forwarded"


def test_api_proxy_x_forwarded_proto(nginx_conf):
    assert re.search(r"proxy_set_header\s+X-Forwarded-Proto\s+\$scheme;", nginx_conf), \
        "X-Forwarded-Proto header must be forwarded"


# --- Health endpoint ---

def test_health_location_block(nginx_conf):
    assert re.search(r"location\s+/health\s*\{", nginx_conf), \
        "location /health block must exist for health checks"


def test_health_returns_200(nginx_conf):
    assert re.search(r"return\s+200", nginx_conf), \
        "/health endpoint must return HTTP 200"


# --- Dockerfile integration ---

def test_dockerfile_copies_nginx_conf(dockerfile_text):
    """Dockerfile must COPY nginx.conf into the nginx conf.d directory."""
    assert re.search(r"COPY\s+nginx\.conf\s+/etc/nginx/conf\.d/default\.conf", dockerfile_text), \
        "Dockerfile must COPY nginx.conf to /etc/nginx/conf.d/default.conf"


def test_dockerfile_no_inline_printf_nginx(dockerfile_text):
    """Dockerfile should not use inline printf to write nginx config."""
    assert "printf" not in dockerfile_text, \
        "Dockerfile must not use inline printf for nginx config; use COPY nginx.conf instead"
