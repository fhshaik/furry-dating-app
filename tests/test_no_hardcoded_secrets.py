from pathlib import Path

from tests.secret_scan import scan_repository, scan_text


def test_scan_text_detects_known_secret_formats():
    aws_key = "AKIA" + "1234567890ABCDEF"
    private_key_marker = "-----BEGIN " + "RSA PRIVATE KEY-----"
    findings = scan_text(
        path=Path("demo.py"),
        text=(
            f'AWS_ACCESS_KEY_ID = "{aws_key}"\n'
            f"private_key = '{private_key_marker}'\n"
        ),
    )

    assert {finding.pattern_name for finding in findings} == {
        "aws_access_key_id",
        "private_key",
    }


def test_scan_text_ignores_placeholders_and_blank_examples():
    aws_docs_example = "AKIA" + "IOSFODNN7EXAMPLE"
    findings = scan_text(
        path=Path(".env.example"),
        text=(
            "JWT_SECRET=changeme\n"
            "GOOGLE_CLIENT_SECRET=\n"
            'DISCORD_CLIENT_SECRET="discord-secret-xyz"\n'
            f'AWS_ACCESS_KEY_ID="{aws_docs_example}"\n'
        ),
    )

    assert findings == []


def test_repository_contains_no_hardcoded_secrets():
    repo_root = Path(__file__).resolve().parents[1]
    findings = scan_repository(repo_root)

    assert findings == [], "\n".join(
        (
            "Potential hardcoded secrets detected:",
            *[
                (
                    f"{finding.path}:{finding.line_number} "
                    f"[{finding.pattern_name}] {finding.excerpt}"
                )
                for finding in findings
            ],
        )
    )
