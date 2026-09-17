"""Deterministic allowlisted fixes and review-record construction."""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
from typing import Iterable

import yaml

from qi_sentinel.models import Finding
from qi_sentinel.policy.config import PolicyConfig
from qi_sentinel.policy.models import RemediationProposal

MASKING_PATH = "mock-platform/snowflake/policies/member_measure.sql"
LOGGING_PATH = "mock-platform/pipelines/logging.yml"
TEST_COMMAND = "python -m pytest"

_MASKING_ATTACHMENT = """ALTER TABLE RPT.MEMBER_MEASURE
  MODIFY COLUMN DOB
  SET MASKING POLICY GOV.PHI_MASK_DOB;
"""


def build_remediation_proposals(
    root: Path,
    findings: Iterable[Finding],
) -> dict[str, RemediationProposal]:
    proposals: dict[str, RemediationProposal] = {}
    for finding in findings:
        if finding.rule_id == "QI-MASK-001":
            proposals[finding.rule_id] = _proposal(
                root,
                finding,
                MASKING_PATH,
                _fixed_masking_content(_read_allowlisted(root, MASKING_PATH)),
            )
        elif finding.rule_id == "QI-LOG-001":
            proposals[finding.rule_id] = _proposal(
                root,
                finding,
                LOGGING_PATH,
                _fixed_logging_content(_read_allowlisted(root, LOGGING_PATH)),
            )
    return proposals


def apply_known_remediation(root: Path, proposal: RemediationProposal) -> bool:
    """Apply one code-owned fix after policy approval; model patches are ignored."""

    expected_path = {
        "QI-MASK-001": MASKING_PATH,
        "QI-LOG-001": LOGGING_PATH,
    }.get(proposal.rule_id)
    if expected_path is None or proposal.files != (expected_path,):
        raise ValueError("Proposal does not match a supported deterministic remediation.")
    before = _read_allowlisted(root, expected_path)
    after = (
        _fixed_masking_content(before)
        if proposal.rule_id == "QI-MASK-001"
        else _fixed_logging_content(before)
    )
    if before == after:
        return False
    _resolve_allowlisted(root, expected_path).write_text(after, encoding="utf-8", newline="\n")
    return True


def build_pull_request_payload(
    proposals: Iterable[RemediationProposal],
    findings: Iterable[Finding],
    *,
    status: str,
) -> dict[str, object] | None:
    proposal_items = tuple(sorted(proposals, key=lambda item: item.rule_id))
    if not proposal_items:
        return None
    finding_map = {finding.rule_id: finding for finding in findings}
    fingerprints = tuple(finding_map[item.rule_id].fingerprint for item in proposal_items)
    identity = hashlib.sha256("\n".join(sorted(fingerprints)).encode("utf-8")).hexdigest()[:12]
    patches = [item.patch for item in proposal_items if item.patch]
    return {
        "local_record_id": f"PR-{identity}",
        "branch": f"qi-sentinel/remediation-{identity}",
        "title": "Restore synthetic masking and log-redaction controls",
        "body": (
            "QI Sentinel prepared two deterministic, policy-approved control restorations. "
            "Human review is required; this payload cannot merge or deploy changes."
        ),
        "status": status,
        "merge": "never",
        "human_review_required": True,
        "files": sorted(path for item in proposal_items for path in item.files),
        "finding_fingerprints": sorted(fingerprints),
        "patch": "\n".join(patches) if patches else None,
        "external_pull_request": None,
    }


def build_escalation(finding: Finding, policy: PolicyConfig) -> dict[str, object]:
    rule = policy.rules[finding.rule_id]
    if finding.rule_id == "QI-SEM-001":
        root_cause = {
            "statement": "The implemented synthetic measure logic differs from the approved specification.",
            "basis": "evidence",
        }
        impact = "The synthetic measure population or result may differ from the approved definition."
        action = "Quality Analytics must review the specification difference and approve any semantic change."
        unavailable = ["Change history and prior semantic approval were not supplied."]
    elif finding.rule_id == "QI-LIN-001":
        root_cause = {
            "statement": "The exported metadata contains no complete lineage record for the required measure.",
            "basis": "evidence",
        }
        impact = "The source-to-run-to-output chain cannot be independently attested from supplied evidence."
        action = "Data Governance must obtain and validate the missing lineage evidence."
        unavailable = ["Missing lineage stages cannot be reconstructed or attested automatically."]
    else:
        raise ValueError(f"No deterministic escalation template exists for {finding.rule_id}.")

    return {
        "local_record_id": f"ESC-{finding.fingerprint[:12]}",
        "status": "open",
        "rule_id": finding.rule_id,
        "finding_fingerprint": finding.fingerprint,
        "disposition": "escalate",
        "expected": finding.expected,
        "observed": finding.observed,
        "root_cause": root_cause,
        "impact": impact,
        "evidence": [item.to_dict() for item in finding.evidence],
        "owner": rule.owner,
        "recommended_next_action": action,
        "proposed_patch": None,
        "unavailable_facts": unavailable,
        "external_record": None,
    }


def _proposal(
    root: Path,
    finding: Finding,
    relative_path: str,
    after: str,
) -> RemediationProposal:
    before = _read_allowlisted(root, relative_path)
    patch = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )
    return RemediationProposal(
        rule_id=finding.rule_id,
        category=finding.category,
        changes_measure_population=False,
        files=(relative_path,),
        commands=(TEST_COMMAND,),
        patch=patch or None,
    )


def _fixed_masking_content(before: str) -> str:
    normalized = " ".join(before.upper().split())
    expected = " ".join(_MASKING_ATTACHMENT.upper().split())
    if expected in normalized:
        return before
    return before.rstrip() + "\n\n" + _MASKING_ATTACHMENT


def _fixed_logging_content(before: str) -> str:
    try:
        payload = yaml.safe_load(before)
    except yaml.YAMLError as error:
        raise ValueError("Logging configuration is not valid YAML.") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("redaction"), dict):
        raise ValueError("Logging configuration must contain a redaction mapping.")
    redaction = payload["redaction"]
    redaction["enabled"] = True
    redaction["fields"] = ["member_id", "date_of_birth", "dob"]
    redaction["replacement"] = "[REDACTED]"
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def _read_allowlisted(root: Path, relative_path: str) -> str:
    path = _resolve_allowlisted(root, relative_path)
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeError) as error:
        raise ValueError(f"Cannot read remediation target: {relative_path}.") from error


def _resolve_allowlisted(root: Path, relative_path: str) -> Path:
    if relative_path not in {MASKING_PATH, LOGGING_PATH}:
        raise ValueError(f"Path is not a built-in remediation target: {relative_path}.")
    resolved_root = root.resolve()
    target = (resolved_root / relative_path).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("Remediation target escapes project root.") from error
    return target
