"""Static security contract for the repository-level GitHub workflow."""

from __future__ import annotations

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = PROJECT_ROOT.parents[1] / ".github/workflows/qi-sentinel.yml"


def test_workflow_uses_only_trusted_triggers_and_pinned_actions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "schedule:" in text
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "@v" not in text
    pins = re.findall(r"uses:\s+[^\s@]+@([0-9a-f]{40})", text)
    assert len(pins) == 8


def test_workflow_permissions_and_codex_boundary_are_explicit() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "contents: read" in text
    assert "contents: write" in text
    assert "pull-requests: write" in text
    assert "github.event.repository.fork == false" in text
    assert text.count("persist-credentials: false") == 3
    assert 'permission-profile: ":read-only"' in text
    assert "secrets.OPENAI_API_KEY" in text
    assert "sk-" not in text
