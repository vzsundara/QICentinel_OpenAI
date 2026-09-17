"""Independent local verification for canonical QI Sentinel evidence packs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from qi_sentinel.evidence.integrity import component_hashes, sha256_bytes, sha256_file, sha256_json
from qi_sentinel.evidence.render import render_evidence_html
from qi_sentinel.evidence.safety import PublicationSafetyError, assert_publishable


@dataclass(frozen=True, slots=True)
class VerificationResult:
    valid: bool
    evidence_path: Path
    checked_source_count: int
    errors: tuple[str, ...]


def verify_evidence_pack(root: Path, artifact: Path) -> VerificationResult:
    root = root.resolve()
    evidence_path = _resolve_evidence_path(root, artifact)
    errors: list[str] = []
    index_path = evidence_path.parent / "index.html"

    try:
        evidence_bytes = evidence_path.read_bytes()
    except OSError:
        return VerificationResult(False, evidence_path, 0, ("evidence.json is missing or unreadable.",))
    try:
        payload = json.loads(evidence_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return VerificationResult(False, evidence_path, 0, ("evidence.json is not valid UTF-8 JSON.",))
    if not isinstance(payload, dict):
        return VerificationResult(False, evidence_path, 0, ("evidence.json must contain an object.",))

    required_keys = {
        "action_result",
        "analysis",
        "approvals",
        "classification",
        "component_hashes",
        "integrity",
        "run",
        "runtime",
        "schema_version",
        "source_manifest",
    }
    if set(payload) != required_keys or payload.get("schema_version") != 1:
        errors.append("Evidence schema or top-level fields are invalid.")

    try:
        assert_publishable(evidence_bytes, label="evidence.json")
    except PublicationSafetyError as error:
        errors.append(str(error))

    integrity = payload.get("integrity")
    if not isinstance(integrity, dict):
        errors.append("Evidence integrity block is missing or invalid.")
        integrity = {}
    expected_evidence_hash = integrity.get("evidence_payload_sha256")
    hash_payload = deepcopy(payload)
    hash_integrity = hash_payload.get("integrity")
    if isinstance(hash_integrity, dict):
        hash_integrity.pop("evidence_payload_sha256", None)
    if expected_evidence_hash != sha256_json(hash_payload):
        errors.append("evidence.json canonical payload hash does not match.")

    index_bytes: bytes | None = None
    try:
        index_bytes = index_path.read_bytes()
    except OSError:
        errors.append("index.html is missing or unreadable.")
    if index_bytes is not None:
        if integrity.get("index_html_sha256") != sha256_bytes(index_bytes):
            errors.append("index.html hash does not match evidence.json.")
        expected_html = render_evidence_html(payload).encode("utf-8")
        if index_bytes != expected_html:
            errors.append("index.html is not the canonical rendering of evidence.json.")
        try:
            assert_publishable(index_bytes, label="index.html")
        except PublicationSafetyError as error:
            errors.append(str(error))

    manifest_value = payload.get("source_manifest")
    manifest = manifest_value if isinstance(manifest_value, list) else []
    if not manifest:
        errors.append("Source manifest is missing or empty.")
    checked = 0
    for index, item in enumerate(manifest):
        if not isinstance(item, dict):
            errors.append(f"Source manifest entry {index} is invalid.")
            continue
        path_value = item.get("path")
        if not isinstance(path_value, str):
            errors.append(f"Source manifest entry {index} has no valid path.")
            continue
        try:
            source = _safe_manifest_path(root, path_value)
        except ValueError as error:
            errors.append(str(error))
            continue
        try:
            observed_size = source.stat().st_size
            observed_hash = sha256_file(source)
        except OSError:
            errors.append(f"Covered source is missing or unreadable: {path_value}.")
            continue
        checked += 1
        if item.get("bytes") != observed_size or item.get("sha256") != observed_hash:
            errors.append(f"Covered source changed: {path_value}.")

    action_result = payload.get("action_result")
    component_value = payload.get("component_hashes")
    if isinstance(action_result, dict) and isinstance(component_value, dict):
        observed_components = component_hashes(action_result, manifest)
        if component_value != observed_components:
            errors.append("One or more component hashes do not match the recorded content.")
    else:
        errors.append("Action result or component hashes are invalid.")

    return VerificationResult(not errors, evidence_path, checked, tuple(errors))


def _resolve_evidence_path(root: Path, artifact: Path) -> Path:
    candidate = artifact if artifact.is_absolute() else root / artifact
    candidate = candidate.resolve()
    if candidate.is_dir():
        candidate = candidate / "evidence.json"
    try:
        candidate.relative_to((root / "artifacts").resolve())
    except ValueError as error:
        raise ValueError("Evidence path must remain under the project artifacts directory.") from error
    return candidate


def _safe_manifest_path(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Covered source path is unsafe: {relative_path}.")
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Covered source path escapes the project: {relative_path}.") from error
    return candidate
