"""Allowlisted, redacted context construction for semantic analysis."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from qi_sentinel.models import Finding

PROMPT_PATH = Path(".github/codex/prompts/monitor.md")
SPEC_PATHS = (
    "specs/synthetic-2026/cbp.yml",
    "specs/synthetic-2026/value_sets.json",
)
REPOSITORY_PATHS = ("mock-platform/measures/cbp/cbp_rate.sql",)
ALLOWED_PATCH_PATH = REPOSITORY_PATHS[0]
REQUIRED_EVIDENCE_PATHS = frozenset((*SPEC_PATHS, *REPOSITORY_PATHS))
MAX_CONTEXT_BYTES = 64 * 1024

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|token|password|secret)\b\s*[:=]\s*['\"]?[^\s,'\"]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]+"),
)


class ContextBuildError(ValueError):
    """Raised when a bounded analysis context cannot be built safely."""


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    prompt: str
    prompt_sha256: str
    input_sha256: str
    allowed_sources: frozenset[str]
    allowed_patch_path: str


def build_analysis_context(root: Path, finding: Finding) -> AnalysisContext:
    """Build the only model context allowed for QI-SEM-001."""

    if finding.rule_id != "QI-SEM-001":
        raise ContextBuildError(f"Unsupported analysis rule: {finding.rule_id!r}.")
    evidence_paths = frozenset(reference.path for reference in finding.evidence)
    if evidence_paths != REQUIRED_EVIDENCE_PATHS:
        raise ContextBuildError("Semantic finding evidence does not match the context allowlist.")

    resolved_root = root.resolve()
    prompt_template = _read_path(resolved_root, PROMPT_PATH)
    spec_excerpts = _load_excerpts(resolved_root, SPEC_PATHS)
    repository_excerpts = _load_excerpts(resolved_root, REPOSITORY_PATHS)
    finding_data = _redact_structure(finding.to_dict())

    canonical_input = _canonical_json(
        {
            "finding": finding_data,
            "spec_excerpts": spec_excerpts,
            "repository_excerpts": repository_excerpts,
            "deterministic_disposition": "escalate",
        }
    )
    prompt = prompt_template
    replacements = {
        "{{FINDING_JSON}}": _safe_embedded_json(finding_data),
        "{{SPEC_EXCERPTS}}": _safe_embedded_json(spec_excerpts),
        "{{REPOSITORY_EXCERPTS}}": _safe_embedded_json(repository_excerpts),
        "{{DETERMINISTIC_DISPOSITION}}": "escalate",
    }
    for placeholder, replacement in replacements.items():
        if prompt.count(placeholder) != 1:
            raise ContextBuildError(f"Prompt template must contain exactly one {placeholder} placeholder.")
        prompt = prompt.replace(placeholder, replacement)

    if len(prompt.encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ContextBuildError("Analysis context exceeds the configured size limit.")

    allowed_sources = frozenset(
        {
            f"finding:{finding.rule_id}",
            *(path.replace("\\", "/") for path in (*SPEC_PATHS, *REPOSITORY_PATHS)),
        }
    )
    return AnalysisContext(
        prompt=prompt,
        prompt_sha256=_sha256(prompt_template),
        input_sha256=_sha256(canonical_input),
        allowed_sources=allowed_sources,
        allowed_patch_path=ALLOWED_PATCH_PATH,
    )


def _load_excerpts(root: Path, relative_paths: tuple[str, ...]) -> list[dict[str, str]]:
    return [
        {"path": relative_path, "content": _redact(_read_path(root, Path(relative_path)))}
        for relative_path in relative_paths
    ]


def _read_path(root: Path, relative_path: Path) -> str:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ContextBuildError(f"Context path escapes project root: {relative_path}.") from error
    try:
        return candidate.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeError) as error:
        raise ContextBuildError(f"Cannot read allowlisted context path: {relative_path}.") from error


def _redact(value: str) -> str:
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def _redact_structure(value: object) -> object:
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, list):
        return [_redact_structure(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_structure(item) for key, item in value.items()}
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _safe_embedded_json(value: object) -> str:
    # Escaping markup characters keeps untrusted text inside its data boundary.
    return _canonical_json(value).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
