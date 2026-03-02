from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_TEXT_FILE_NAMES = {
    ".env",
    ".env.example",
    "Dockerfile",
    "docker-compose.local.yml",
    "docker-compose.prod.yml",
}

_TEXT_FILE_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".mako",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

_SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".ralphy-worktrees",
    ".ralphy-sandboxes",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}

_PLACEHOLDER_MARKERS = (
    "changeme",
    "dummy",
    "example",
    "fake",
    "placeholder",
    "sample",
    "test",
)

_SECRET_PATTERNS = {
    "aws_access_key_id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_pat": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    "github_fine_grained_pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    "private_key": re.compile(
        r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----"
    ),
    "slack_token": re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    "stripe_live_secret": re.compile(r"\bsk_live_[0-9A-Za-z]{16,}\b"),
}

_GENERIC_SECRET_ASSIGNMENT = re.compile(
    r"""
    \b
    (?:api[_-]?key|access[_-]?key|secret|token|password|client[_-]?secret)
    \b
    [^=\n:]{0,40}
    [=:]
    \s*
    ["']
    (?P<value>[A-Za-z0-9/+_=.-]{24,})
    ["']
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class SecretFinding:
    path: Path
    line_number: int
    pattern_name: str
    excerpt: str


def _is_text_file(path: Path) -> bool:
    return path.name in _TEXT_FILE_NAMES or path.suffix in _TEXT_FILE_SUFFIXES


def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _is_placeholder(value: str) -> bool:
    normalized = value.lower()
    return any(marker in normalized for marker in _PLACEHOLDER_MARKERS)


def _scan_line(path: Path, line: str, line_number: int) -> list[SecretFinding]:
    findings: list[SecretFinding] = []

    for pattern_name, pattern in _SECRET_PATTERNS.items():
        if match := pattern.search(line):
            if _is_placeholder(match.group(0)):
                continue
            findings.append(
                SecretFinding(
                    path=path,
                    line_number=line_number,
                    pattern_name=pattern_name,
                    excerpt=match.group(0),
                )
            )

    if match := _GENERIC_SECRET_ASSIGNMENT.search(line):
        value = match.group("value")
        if not _is_placeholder(value):
            findings.append(
                SecretFinding(
                    path=path,
                    line_number=line_number,
                    pattern_name="generic_secret_assignment",
                    excerpt=value,
                )
            )

    return findings


def scan_text(path: Path, text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        findings.extend(_scan_line(path=path, line=line, line_number=line_number))

    return findings


def scan_repository(root: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []

    for path in sorted(root.rglob("*")):
        if path.is_dir() or _should_skip(path) or not _is_text_file(path):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        findings.extend(scan_text(path=path.relative_to(root), text=text))

    return findings
