"""Local Phase 4 scan, gate, test, action, and record orchestration."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from qi_sentinel.policy.actions import (
    TEST_COMMAND,
    apply_known_remediation,
    build_escalation,
    build_pull_request_payload,
    build_remediation_proposals,
)
from qi_sentinel.policy.config import PolicyConfig
from qi_sentinel.policy.gate import PolicyGate
from qi_sentinel.policy.models import ActionCycleResult, RemediationProposal, TestResult, ordered_decisions
from qi_sentinel.policy.store import ActionStore
from qi_sentinel.scanners import ScanContext, scan_platform

TestRunner = Callable[[Path, tuple[str, ...]], TestResult]


def run_action_cycle(
    root: Path,
    *,
    mode: str | None = None,
    state_path: Path = Path("artifacts/phase4/action-state.json"),
    test_runner: TestRunner | None = None,
) -> ActionCycleResult:
    root = root.resolve()
    policy = PolicyConfig.load(root / "config" / "policy.yml")
    selected_mode = mode or policy.mode
    if selected_mode not in {"enforce", "observe"}:
        raise ValueError("Mode must be enforce or observe.")

    findings = scan_platform(ScanContext.from_root(root))
    proposals = build_remediation_proposals(root, findings)
    gate = PolicyGate(policy)

    # Evaluate static controls first to identify the only changes worth staging.
    static_decisions = {
        finding.rule_id: gate.evaluate(
            finding,
            proposals.get(finding.rule_id),
            tests_passed=True,
            submitted_for_human_review=True,
            mode="enforce",
        )
        for finding in findings
    }
    staged_proposals = tuple(
        proposals[rule_id]
        for rule_id, decision in sorted(static_decisions.items())
        if decision.disposition == "auto-fix"
    )
    runner = test_runner or _run_required_tests
    test_result = _test_staged_changes(root, staged_proposals, runner)

    decisions = ordered_decisions(
        gate.evaluate(
            finding,
            proposals.get(finding.rule_id),
            tests_passed=test_result.passed,
            submitted_for_human_review=True,
            mode=selected_mode,
        )
        for finding in findings
    )
    decision_map = {decision.rule_id: decision for decision in decisions}
    approved = tuple(
        proposal
        for rule_id, proposal in sorted(proposals.items())
        if decision_map[rule_id].disposition == "auto-fix"
    )

    applied_files: list[str] = []
    if selected_mode == "enforce":
        for proposal in approved:
            if apply_known_remediation(root, proposal):
                applied_files.extend(proposal.files)

    review_proposals = staged_proposals
    if selected_mode == "observe":
        pr_status = "observe-only"
    elif approved:
        pr_status = "prepared"
    else:
        pr_status = "held"
    pull_request = build_pull_request_payload(
        review_proposals,
        findings,
        status=pr_status,
    )

    finding_map = {finding.rule_id: finding for finding in findings}
    escalations = tuple(
        build_escalation(finding_map[decision.rule_id], policy)
        for decision in decisions
        if decision.disposition == "escalate"
    )
    store = ActionStore(root, state_path)
    stored_pr, stored_escalations = store.update(pull_request, escalations)

    return ActionCycleResult(
        mode=selected_mode,
        findings=findings,
        decisions=decisions,
        test_result=test_result,
        applied_files=tuple(sorted(set(applied_files))),
        pull_request=stored_pr,
        escalations=stored_escalations,
        state_path=store.path.relative_to(root).as_posix(),
    )


def _test_staged_changes(
    root: Path,
    proposals: tuple[RemediationProposal, ...],
    runner: TestRunner,
) -> TestResult:
    commands = (TEST_COMMAND,)
    if not proposals:
        return runner(root, commands)
    with tempfile.TemporaryDirectory(prefix="qi-sentinel-phase4-") as temporary:
        stage = Path(temporary) / "repository" / "Deliverable" / "Src"
        shutil.copytree(
            root,
            stage,
            ignore=shutil.ignore_patterns(".venv", "artifacts", ".pytest_cache", "__pycache__", "*.pyc"),
        )
        repository_workflow = root.parents[1] / ".github" / "workflows" / "qi-sentinel.yml"
        if repository_workflow.is_file():
            staged_workflow = stage.parents[1] / ".github" / "workflows" / "qi-sentinel.yml"
            staged_workflow.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repository_workflow, staged_workflow)
        for proposal in proposals:
            apply_known_remediation(stage, proposal)
        return runner(stage, commands)


def _run_required_tests(root: Path, commands: tuple[str, ...]) -> TestResult:
    if commands != (TEST_COMMAND,):
        return TestResult(TEST_COMMAND, False, 2, "Required command set did not match the policy allowlist.")
    environment = os.environ.copy()
    source_path = str(root / "src")
    existing_python_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not existing_python_path else source_path + os.pathsep + existing_python_path
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return TestResult(TEST_COMMAND, False, 2, "Required pytest execution was unavailable or timed out.")
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    summary = lines[-1][:500] if lines else f"pytest exited with code {completed.returncode}."
    return TestResult(TEST_COMMAND, completed.returncode == 0, completed.returncode, summary)
