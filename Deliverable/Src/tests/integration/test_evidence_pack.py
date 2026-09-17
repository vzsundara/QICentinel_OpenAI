"""Integration tests for canonical evidence generation and verification."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from qi_sentinel.evidence import (
    EvidenceGenerationError,
    PublicationSafetyError,
    assert_publishable,
    generate_evidence_pack,
    verify_evidence_pack,
)
from qi_sentinel.policy import TestResult as ActionTestResult
from qi_sentinel.policy import run_action_cycle

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _copy_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(
        PROJECT_ROOT,
        root,
        ignore=shutil.ignore_patterns(".venv", "artifacts", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    return root


def _passing_runner(root: Path, commands: tuple[str, ...]) -> ActionTestResult:
    return ActionTestResult("python -m pytest", True, 0, "synthetic test runner passed")


def _failing_runner(root: Path, commands: tuple[str, ...]) -> ActionTestResult:
    return ActionTestResult("python -m pytest", False, 1, "synthetic test runner failed")


def _generate(root: Path, run_id: str):
    result = run_action_cycle(root, mode="observe", test_runner=_passing_runner)
    return generate_evidence_pack(
        root,
        run_id=run_id,
        action_result=result,
        generated_at="2026-09-17T12:00:00Z",
        repository_commit="a" * 40,
    )


def test_generated_pack_is_publishable_and_verifies(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    pack = _generate(root, "verified-run")

    result = verify_evidence_pack(root, pack.directory)
    payload = json.loads(pack.evidence_path.read_text(encoding="utf-8"))
    raw_member_identifier = "SYNTH-" + "MEMBER-0007"

    assert result.valid is True
    assert result.checked_source_count == len(payload["source_manifest"])
    assert payload["action_result"]["finding_count"] == 4
    assert len(payload["action_result"]["escalations"]) == 2
    assert payload["approvals"] == {
        "external_approval_id": None,
        "human_review_required": True,
        "merge": "never",
        "status": "not-recorded",
    }
    assert payload["analysis"]["status"] == "not-run"
    assert raw_member_identifier not in pack.evidence_path.read_text(encoding="utf-8")
    assert raw_member_identifier not in pack.index_path.read_text(encoding="utf-8")


def test_failed_required_tests_block_evidence_publication(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    result = run_action_cycle(root, mode="observe", test_runner=_failing_runner)

    with pytest.raises(EvidenceGenerationError, match="Required tests did not pass"):
        generate_evidence_pack(root, run_id="blocked-run", action_result=result)

    assert not (root / "artifacts" / "blocked-run").exists()


def test_modified_evidence_fails_verification(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    pack = _generate(root, "tampered-evidence")
    payload = json.loads(pack.evidence_path.read_text(encoding="utf-8"))
    payload["approvals"]["status"] = "approved"
    pack.evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_evidence_pack(root, pack.directory)

    assert result.valid is False
    assert "evidence.json canonical payload hash does not match." in result.errors


def test_modified_or_missing_html_fails_verification(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    modified = _generate(root, "tampered-html")
    modified.index_path.write_text("<html>changed</html>", encoding="utf-8")
    missing = _generate(root, "missing-html")
    missing.index_path.unlink()

    modified_result = verify_evidence_pack(root, modified.directory)
    missing_result = verify_evidence_pack(root, missing.directory)

    assert modified_result.valid is False
    assert "index.html hash does not match evidence.json." in modified_result.errors
    assert missing_result.valid is False
    assert "index.html is missing or unreadable." in missing_result.errors


def test_changed_or_missing_covered_source_fails_verification(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    pack = _generate(root, "changed-source")
    source = root / "specs/synthetic-2026/col.yml"
    source.write_text(source.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    changed = verify_evidence_pack(root, pack.directory)
    source.unlink()
    missing = verify_evidence_pack(root, pack.directory)

    assert changed.valid is False
    assert "Covered source changed: specs/synthetic-2026/col.yml." in changed.errors
    assert missing.valid is False
    assert "Covered source is missing or unreadable: specs/synthetic-2026/col.yml." in missing.errors


@pytest.mark.parametrize(
    "candidate",
    [
        "OPENAI_API_KEY=" + "sk-" + "examplevalue123456",
        '{"member_id":"' + "SYNTH-" + 'MEMBER-9999"}',
        '{"date_of_birth":"1980-02-03"}',
    ],
)
def test_publication_safety_rejects_secrets_and_raw_synthetic_values(candidate: str) -> None:
    with pytest.raises(PublicationSafetyError):
        assert_publishable(candidate, label="candidate")
