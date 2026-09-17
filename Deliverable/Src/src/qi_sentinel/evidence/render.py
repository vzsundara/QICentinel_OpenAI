"""Deterministic reviewer-facing HTML derived from canonical evidence JSON."""

from __future__ import annotations

from html import escape
from typing import Mapping


def render_evidence_html(payload: Mapping[str, object]) -> str:
    run = _mapping(payload.get("run"))
    action = _mapping(payload.get("action_result"))
    approvals = _mapping(payload.get("approvals"))
    findings = _list(action.get("findings"))
    decisions = _list(action.get("decisions"))
    escalations = _list(action.get("escalations"))
    manifest = _list(payload.get("source_manifest"))
    decision_by_rule = {
        str(item.get("rule_id")): item
        for item in decisions
        if isinstance(item, dict)
    }

    finding_rows = "".join(
        "<tr>"
        f"<td><code>{_text(item.get('rule_id'))}</code></td>"
        f"<td>{_text(item.get('severity'))}</td>"
        f"<td>{_text(decision_by_rule.get(str(item.get('rule_id')), {}).get('disposition'))}</td>"
        f"<td>{_text(item.get('expected'))}</td>"
        f"<td>{_text(item.get('observed'))}</td>"
        "</tr>"
        for item in findings
        if isinstance(item, dict)
    )
    manifest_rows = "".join(
        "<tr>"
        f"<td><code>{_text(item.get('path'))}</code></td>"
        f"<td>{_text(item.get('category'))}</td>"
        f"<td><code>{_text(item.get('sha256'))}</code></td>"
        "</tr>"
        for item in manifest
        if isinstance(item, dict)
    )
    tests = _mapping(action.get("test_result"))
    pull_request = _mapping(action.get("pull_request"))
    status = "PASS" if tests.get("passed") is True else "FAIL"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QI Sentinel Evidence — {_text(run.get('run_id'))}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, system-ui, sans-serif; }}
    body {{ margin: 0 auto; max-width: 1180px; padding: 2rem; color: #172033; background: #f6f8fb; }}
    h1, h2 {{ color: #102a43; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 1rem; }}
    .card {{ background: white; border: 1px solid #d9e2ec; border-radius: .6rem; padding: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; background: white; font-size: .9rem; }}
    th, td {{ border: 1px solid #d9e2ec; padding: .6rem; text-align: left; vertical-align: top; }}
    th {{ background: #eaf2f8; }}
    code {{ overflow-wrap: anywhere; }}
    .pass {{ color: #146c43; font-weight: 700; }}
    .notice {{ border-left: .35rem solid #486581; padding-left: 1rem; }}
  </style>
</head>
<body>
  <h1>QI Sentinel Evidence</h1>
  <p class="notice">Synthetic control-plane proof of concept. This report is derived from <code>evidence.json</code> and is not an independent source of truth.</p>
  <section class="summary">
    <div class="card"><strong>Run</strong><br>{_text(run.get('run_id'))}</div>
    <div class="card"><strong>Generated</strong><br>{_text(run.get('generated_at'))}</div>
    <div class="card"><strong>Mode</strong><br>{_text(action.get('mode'))}</div>
    <div class="card"><strong>Findings</strong><br>{len(findings)}</div>
    <div class="card"><strong>Escalations</strong><br>{len(escalations)}</div>
    <div class="card"><strong>Tests</strong><br><span class="pass">{escape(status)}</span> {_text(tests.get('summary'))}</div>
  </section>
  <h2>Review controls</h2>
  <ul>
    <li>Merge policy: <code>{_text(pull_request.get('merge'))}</code></li>
    <li>Human review required: <code>{_text(approvals.get('human_review_required'))}</code></li>
    <li>Approval status: <code>{_text(approvals.get('status'))}</code></li>
    <li>External pull request: <code>{_text(pull_request.get('external_pull_request'))}</code></li>
  </ul>
  <h2>Findings and dispositions</h2>
  <table><thead><tr><th>Rule</th><th>Severity</th><th>Disposition</th><th>Expected</th><th>Observed</th></tr></thead><tbody>{finding_rows}</tbody></table>
  <h2>Covered sources</h2>
  <table><thead><tr><th>Path</th><th>Category</th><th>SHA-256</th></tr></thead><tbody>{manifest_rows}</tbody></table>
</body>
</html>
"""


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _text(value: object) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    return escape(str(value))
