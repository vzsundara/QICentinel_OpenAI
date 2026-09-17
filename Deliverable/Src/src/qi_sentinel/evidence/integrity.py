"""Canonical serialization and SHA-256 helpers shared by evidence services."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_bytes(canonical_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def component_hashes(
    action_result: Mapping[str, object],
    source_manifest: list[dict[str, object]],
) -> dict[str, str]:
    def entries(*categories: str) -> list[dict[str, object]]:
        allowed = set(categories)
        return [item for item in source_manifest if item.get("category") in allowed]

    actions = {
        "applied_files": action_result.get("applied_files"),
        "decisions": action_result.get("decisions"),
        "escalations": action_result.get("escalations"),
        "pull_request": action_result.get("pull_request"),
    }
    tests = {
        "result": action_result.get("test_result"),
        "sources": entries("test"),
    }
    return {
        "inputs_sha256": sha256_json(entries("configuration", "input", "test-fixture", "runtime")),
        "specification_sha256": sha256_json(entries("specification")),
        "policy_sha256": sha256_json(entries("policy")),
        "prompt_sha256": sha256_json(entries("prompt")),
        "findings_sha256": sha256_json(action_result.get("findings")),
        "actions_sha256": sha256_json(actions),
        "tests_sha256": sha256_json(tests),
        "result_sha256": sha256_json(action_result),
    }
