"""Integration tests for Phase 4 local action planning and idempotency."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

from qi_sentinel.policy import TestResult as ActionTestResult
from qi_sentinel.policy import run_action_cycle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASKING_PATH = Path("mock-platform/snowflake/policies/member_measure.sql")
LOGGING_PATH = Path("mock-platform/pipelines/logging.yml")


def _copy_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(
        PROJECT_ROOT,
        root,
        ignore=shutil.ignore_patterns(".venv", "artifacts", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    return root


def _passing_runner(root: Path, commands: tuple[str, ...]) -> ActionTestResult:
    assert commands == ("python -m pytest",)
    masking = (root / MASKING_PATH).read_text(encoding="utf-8")
    logging = (root / LOGGING_PATH).read_text(encoding="utf-8")
    assert "SET MASKING POLICY GOV.PHI_MASK_DOB" in masking
    assert "enabled: true" in logging
    return ActionTestResult("python -m pytest", True, 0, "synthetic test runner passed")


def _failing_runner(root: Path, commands: tuple[str, ...]) -> ActionTestResult:
    return ActionTestResult("python -m pytest", False, 1, "synthetic test failure")


def test_enforce_mode_prepares_two_fixes_and_two_escalations(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    expected_applied = tuple(
        path.as_posix()
        for path, marker in (
            (LOGGING_PATH, "enabled: true"),
            (MASKING_PATH, "SET MASKING POLICY GOV.PHI_MASK_DOB"),
        )
        if marker not in (root / path).read_text(encoding="utf-8")
    )

    result = run_action_cycle(root, mode="enforce", test_runner=_passing_runner)

    dispositions = {item.rule_id: item.disposition for item in result.decisions}
    assert dispositions == {
        "QI-LIN-001": "escalate",
        "QI-LOG-001": "auto-fix",
        "QI-MASK-001": "auto-fix",
        "QI-SEM-001": "escalate",
    }
    assert result.applied_files == expected_applied
    assert "enabled: true" in (root / LOGGING_PATH).read_text(encoding="utf-8")
    assert "SET MASKING POLICY GOV.PHI_MASK_DOB" in (root / MASKING_PATH).read_text(encoding="utf-8")
    assert result.pull_request is not None
    assert result.pull_request["merge"] == "never"
    assert result.pull_request["external_pull_request"] is None
    assert result.pull_request["files"] == [LOGGING_PATH.as_posix(), MASKING_PATH.as_posix()]
    assert [item["rule_id"] for item in result.escalations] == ["QI-LIN-001", "QI-SEM-001"]
    assert all(item["external_record"] is None for item in result.escalations)


def test_observe_mode_changes_no_files(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    before = {
        path.as_posix(): (root / path).read_bytes()
        for path in (MASKING_PATH, LOGGING_PATH)
    }

    result = run_action_cycle(root, mode="observe", test_runner=_passing_runner)

    assert result.applied_files == ()
    assert result.pull_request is not None
    assert result.pull_request["status"] == "observe-only"
    assert {item.rule_id: item.disposition for item in result.decisions} == {
        "QI-LIN-001": "escalate",
        "QI-LOG-001": "held",
        "QI-MASK-001": "held",
        "QI-SEM-001": "escalate",
    }
    assert all((root / path).read_bytes() == content for path, content in before.items())


def test_failed_tests_hold_fixes_and_apply_nothing(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    before = (root / MASKING_PATH).read_bytes(), (root / LOGGING_PATH).read_bytes()

    result = run_action_cycle(root, mode="enforce", test_runner=_failing_runner)

    dispositions = {item.rule_id: item.disposition for item in result.decisions}
    assert dispositions["QI-MASK-001"] == "held"
    assert dispositions["QI-LOG-001"] == "held"
    assert result.applied_files == ()
    assert result.pull_request is not None
    assert result.pull_request["status"] == "held"
    assert before == ((root / MASKING_PATH).read_bytes(), (root / LOGGING_PATH).read_bytes())


def test_identical_rerun_updates_records_without_duplicates(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)

    first = run_action_cycle(root, mode="enforce", test_runner=_passing_runner)
    second = run_action_cycle(root, mode="enforce", test_runner=_passing_runner)
    state = json.loads((root / "artifacts/phase4/action-state.json").read_text(encoding="utf-8"))

    assert first.pull_request["local_record_id"] == second.pull_request["local_record_id"]
    assert second.pull_request["revision"] == 2
    assert [item["local_record_id"] for item in first.escalations] == [
        item["local_record_id"] for item in second.escalations
    ]
    assert all(item["revision"] == 2 for item in second.escalations)
    assert len(state["pull_requests"]) == 1
    assert len(state["escalations"]) == 2
