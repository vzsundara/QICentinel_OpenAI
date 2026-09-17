"""Create immutable, canonical evidence packs from deterministic action results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess

from qi_sentinel import __version__
from qi_sentinel.evidence.integrity import (
    component_hashes,
    sha256_bytes,
    sha256_file,
    sha256_json,
)
from qi_sentinel.evidence.render import render_evidence_html
from qi_sentinel.evidence.safety import assert_publishable
from qi_sentinel.policy.models import ActionCycleResult

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class EvidenceGenerationError(ValueError):
    """Raised when a complete and honest evidence pack cannot be generated."""


@dataclass(frozen=True, slots=True)
class EvidencePack:
    directory: Path
    evidence_path: Path
    index_path: Path
    evidence_payload_sha256: str
    index_html_sha256: str


def generate_evidence_pack(
    root: Path,
    *,
    run_id: str,
    action_result: ActionCycleResult,
    generated_at: str | None = None,
    repository_commit: str | None = None,
) -> EvidencePack:
    root = root.resolve()
    if not action_result.test_result.passed:
        raise EvidenceGenerationError("Required tests did not pass; evidence publication is blocked.")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise EvidenceGenerationError("Run ID must use only letters, digits, dot, underscore, and hyphen.")
    output_directory = (root / "artifacts" / run_id).resolve()
    _require_within(output_directory, root / "artifacts", "Evidence directory")
    if output_directory.exists() and any(output_directory.iterdir()):
        raise EvidenceGenerationError(f"Evidence directory is not empty: artifacts/{run_id}.")

    source_manifest = _source_manifest(root)
    action_payload = action_result.to_dict()
    prompt_entry = next(item for item in source_manifest if item["category"] == "prompt")
    payload: dict[str, object] = {
        "schema_version": 1,
        "classification": {
            "data": "synthetic-only",
            "control_plane_only": True,
            "publishable_content_checked": True,
        },
        "run": {
            "run_id": run_id,
            "generated_at": generated_at or _utc_now(),
            "repository_commit": repository_commit or _repository_commit(root),
        },
        "runtime": {
            "python": platform.python_version(),
            "qi_sentinel": __version__,
            "openai_codex": _package_version("openai-codex"),
            "platform": platform.system().lower(),
        },
        "analysis": {
            "status": "not-run",
            "provider": None,
            "prompt_sha256": prompt_entry["sha256"],
            "input_sha256": None,
            "response_sha256": None,
            "unavailable_facts": [
                "No live Codex analysis was requested for this deterministic evidence run."
            ],
        },
        "action_result": action_payload,
        "approvals": {
            "human_review_required": True,
            "status": "not-recorded",
            "merge": "never",
            "external_approval_id": None,
        },
        "source_manifest": source_manifest,
        "component_hashes": component_hashes(action_payload, source_manifest),
    }

    # The renderer deliberately omits the integrity block, avoiding a circular
    # dependency while keeping the HTML reproducible from the canonical payload.
    index_text = render_evidence_html(payload)
    index_bytes = index_text.encode("utf-8")
    index_sha256 = sha256_bytes(index_bytes)
    payload["integrity"] = {"index_html_sha256": index_sha256}
    evidence_sha256 = sha256_json(payload)
    payload["integrity"]["evidence_payload_sha256"] = evidence_sha256
    evidence_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"

    assert_publishable(evidence_bytes, label="evidence.json")
    assert_publishable(index_bytes, label="index.html")

    output_directory.mkdir(parents=True, exist_ok=True)
    _atomic_write(output_directory / "evidence.json", evidence_bytes)
    _atomic_write(output_directory / "index.html", index_bytes)
    return EvidencePack(
        directory=output_directory,
        evidence_path=output_directory / "evidence.json",
        index_path=output_directory / "index.html",
        evidence_payload_sha256=evidence_sha256,
        index_html_sha256=index_sha256,
    )


def _source_manifest(root: Path) -> list[dict[str, object]]:
    paths: dict[str, str] = {
        "config/policy.yml": "policy",
        "config/sentinel.yml": "configuration",
        ".github/codex/prompts/monitor.md": "prompt",
        "pyproject.toml": "runtime",
        "tests/fixtures/seeds.json": "input",
    }
    _add_tree(paths, root, "mock-platform", "input")
    _add_tree(paths, root, "specs/synthetic-2026", "specification")
    _add_tree(paths, root, "tests/fixtures", "test-fixture")
    for path in sorted((root / "tests").rglob("*.py")):
        paths[path.relative_to(root).as_posix()] = "test"

    manifest: list[dict[str, object]] = []
    for relative_path, category in sorted(paths.items()):
        path = _safe_source_path(root, relative_path)
        try:
            size = path.stat().st_size
            digest = sha256_file(path)
        except (FileNotFoundError, OSError) as error:
            raise EvidenceGenerationError(f"Required evidence source is unavailable: {relative_path}.") from error
        manifest.append(
            {
                "path": relative_path,
                "category": category,
                "bytes": size,
                "sha256": digest,
            }
        )
    return manifest


def _add_tree(paths: dict[str, str], root: Path, relative_directory: str, category: str) -> None:
    directory = _safe_source_path(root, relative_directory)
    if not directory.is_dir():
        raise EvidenceGenerationError(f"Required evidence source directory is unavailable: {relative_directory}.")
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        paths[path.relative_to(root).as_posix()] = category


def _safe_source_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    _require_within(candidate, root, "Evidence source")
    return candidate


def _require_within(candidate: Path, parent: Path, label: str) -> None:
    try:
        candidate.relative_to(parent.resolve())
    except ValueError as error:
        raise EvidenceGenerationError(f"{label} escapes the project boundary.") from error


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _repository_commit(root: Path) -> str:
    github_sha = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-fA-F]{40,64}", github_sha):
        return github_sha.lower()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    value = completed.stdout.strip()
    return value.lower() if completed.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40,64}", value) else "unavailable"


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"
