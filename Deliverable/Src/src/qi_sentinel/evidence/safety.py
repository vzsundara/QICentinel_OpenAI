"""Publication checks for secrets and raw synthetic sensitive values."""

from __future__ import annotations

import re


class PublicationSafetyError(ValueError):
    """Raised when a candidate evidence artifact is unsafe to publish."""


_FORBIDDEN_PATTERNS = (
    (
        "openai_api_key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b"),
    ),
    (
        "github_token",
        re.compile(r"\b(?:gh[psuro]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\b\s*[:=]\s*"
            r"[\"']?(?!\[REDACTED\])[^\s,\"']{8,}"
        ),
    ),
    (
        "authorization_header",
        re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+(?!\[REDACTED\])[A-Za-z0-9._~-]{8,}"),
    ),
    (
        "synthetic_member_identifier",
        re.compile(r"\bSYNTH-MEMBER-[A-Za-z0-9_-]+\b", flags=re.IGNORECASE),
    ),
    (
        "raw_member_field",
        re.compile(r'(?i)[\"\']member_id[\"\']\s*:\s*[\"\'](?!\[REDACTED\])[^\"\']+[\"\']'),
    ),
    (
        "raw_birth_date_field",
        re.compile(
            r'(?i)[\"\'](?:date_of_birth|dob)[\"\']\s*:\s*'
            r'[\"\'](?!\[REDACTED\])\d{4}-\d{2}-\d{2}[\"\']'
        ),
    ),
)


def assert_publishable(content: bytes | str, *, label: str) -> None:
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PublicationSafetyError(f"{label} is not valid UTF-8.") from error
    else:
        text = content
    for code, pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(text):
            raise PublicationSafetyError(f"{label} failed publication safety check: {code}.")
