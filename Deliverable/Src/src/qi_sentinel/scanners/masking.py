"""Deterministic scanner for missing synthetic masking-policy attachments."""

from __future__ import annotations

import re

from qi_sentinel.models import EvidenceReference, Finding
from qi_sentinel.scanners.base import ScanContext, ScanInputError, load_json, read_text, require_list, require_mapping

RULE_ID = "QI-MASK-001"
EXPECTED_POLICIES = {
    "RPT.MEMBER_MEASURE.DOB": "GOV.PHI_MASK_DOB",
}


def scan(context: ScanContext) -> list[Finding]:
    columns_path = context.platform_path / "snowflake" / "information_schema" / "columns.json"
    policy_path = context.platform_path / "snowflake" / "policies" / "member_measure.sql"

    payload = require_mapping(load_json(columns_path), columns_path)
    columns = require_list(payload.get("columns"), columns_path, "columns")
    policy_sql = read_text(policy_path)

    findings: list[Finding] = []
    normalized_columns: list[dict[str, object]] = []
    for index, item in enumerate(columns):
        normalized_columns.append(require_mapping(item, columns_path, f"columns[{index}]"))

    for column in sorted(
        normalized_columns,
        key=lambda item: (
            str(item.get("table_schema", "")),
            str(item.get("table_name", "")),
            str(item.get("column_name", "")),
        ),
    ):
        if str(column.get("tag", "")).upper() != "SYNTHETIC_PHI":
            continue

        schema = _required_name(column, "table_schema", columns_path)
        table = _required_name(column, "table_name", columns_path)
        name = _required_name(column, "column_name", columns_path)
        target = f"{schema}.{table}.{name}"
        expected_policy = EXPECTED_POLICIES.get(target)
        if expected_policy is None:
            continue

        export_policy = column.get("masking_policy")
        export_matches = isinstance(export_policy, str) and export_policy.upper() == expected_policy
        ddl_matches = _has_attachment(policy_sql, schema, table, name, expected_policy)
        if export_matches and ddl_matches:
            continue

        gaps: list[str] = []
        if not export_matches:
            state = "none" if export_policy is None else str(export_policy)
            gaps.append(f"metadata export reports masking policy {state!r}")
        if not ddl_matches:
            gaps.append("policy DDL has no matching attachment statement")

        findings.append(
            Finding(
                rule_id=RULE_ID,
                title="Masking policy is missing from a tagged reporting column",
                severity="critical",
                confidence=1.0,
                category="access-control-restoration",
                target=target,
                expected=f"{target} is protected by {expected_policy}.",
                observed="; ".join(gaps) + ".",
                evidence=(
                    EvidenceReference(
                        context.display_path(columns_path),
                        f"Synthetic PHI tag and masking-policy field for {target}.",
                    ),
                    EvidenceReference(
                        context.display_path(policy_path),
                        f"Approved policy definition and attachment statements for {target}.",
                    ),
                ),
            )
        )

    return findings


def _required_name(column: dict[str, object], key: str, path: object) -> str:
    value = column.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ScanInputError(path, f"column field {key!r} must be a non-empty string")
    return value.upper()


def _has_attachment(sql: str, schema: str, table: str, column: str, policy: str) -> bool:
    pattern = re.compile(
        rf"ALTER\s+TABLE\s+{re.escape(schema)}\.{re.escape(table)}\s+"
        rf"MODIFY\s+COLUMN\s+{re.escape(column)}\s+SET\s+MASKING\s+POLICY\s+{re.escape(policy)}\b",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return pattern.search(sql) is not None
