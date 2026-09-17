"""Deterministic scanner for missing synthetic measure lineage."""

from __future__ import annotations

from qi_sentinel.models import EvidenceReference, Finding
from qi_sentinel.scanners.base import ScanContext, ScanInputError, load_json, load_yaml, require_list, require_mapping

RULE_ID = "QI-LIN-001"


def scan(context: ScanContext) -> list[Finding]:
    lineage_path = context.platform_path / "lineage" / "measures.json"
    lineage = require_mapping(load_json(lineage_path), lineage_path)
    records_value = require_list(lineage.get("records"), lineage_path, "records")

    records: dict[str, dict[str, object]] = {}
    for index, value in enumerate(records_value):
        record = require_mapping(value, lineage_path, f"records[{index}]")
        measure_id = record.get("measure_id")
        if not isinstance(measure_id, str) or not measure_id.strip():
            raise ScanInputError(lineage_path, f"records[{index}].measure_id must be a non-empty string")
        records[measure_id.upper()] = record

    findings: list[Finding] = []
    for spec_path in sorted(context.specification_path.glob("*.yml")):
        spec = require_mapping(load_yaml(spec_path), spec_path)
        controls_value = spec.get("control_expectations", {})
        controls = require_mapping(controls_value, spec_path, "control_expectations")
        if controls.get("lineage_required") is not True:
            continue

        measure_id = _required_measure_id(spec, spec_path)
        stage_value = controls.get("required_stages")
        stages = require_list(stage_value, spec_path, "control_expectations.required_stages")
        if not stages or not all(isinstance(stage, str) and stage for stage in stages):
            raise ScanInputError(spec_path, "required lineage stages must contain non-empty strings")

        record = records.get(measure_id)
        gaps: list[str] = []
        if record is None:
            gaps.append("no lineage record exists")
        else:
            missing_stages = sorted(
                stage for stage in stages if not isinstance(record.get(stage), str) or not str(record.get(stage)).strip()
            )
            if missing_stages:
                gaps.append("record is missing stages: " + ", ".join(missing_stages))
        if not gaps:
            continue

        findings.append(
            Finding(
                rule_id=RULE_ID,
                title="Required synthetic measure lineage is missing or incomplete",
                severity="medium",
                confidence=1.0,
                category="evidence-attestation",
                target=measure_id,
                expected=f"{measure_id} has a complete lineage chain: " + ", ".join(stages) + ".",
                observed="; ".join(gaps) + ".",
                evidence=(
                    EvidenceReference(
                        context.display_path(spec_path),
                        f"Synthetic lineage requirement for {measure_id}.",
                    ),
                    EvidenceReference(
                        context.display_path(lineage_path),
                        f"Exported synthetic lineage records checked for {measure_id}.",
                    ),
                ),
            )
        )

    return findings


def _required_measure_id(spec: dict[str, object], path: object) -> str:
    value = spec.get("measure_id")
    if not isinstance(value, str) or not value.strip():
        raise ScanInputError(path, "measure_id must be a non-empty string")
    return value.upper()
