"""Deterministic scanner for unredacted synthetic log fields."""

from __future__ import annotations

import json

from qi_sentinel.models import EvidenceReference, Finding
from qi_sentinel.scanners.base import ScanContext, ScanInputError, load_yaml, read_text, require_mapping

RULE_ID = "QI-LOG-001"
SENSITIVE_FIELDS = frozenset({"member_id", "date_of_birth", "dob"})


def scan(context: ScanContext) -> list[Finding]:
    config_path = context.platform_path / "pipelines" / "logging.yml"
    log_path = context.platform_path / "logs" / "measure-runner.log"

    config = require_mapping(load_yaml(config_path), config_path)
    redaction = require_mapping(config.get("redaction"), config_path, "redaction")
    enabled = redaction.get("enabled") is True
    replacement = redaction.get("replacement", "[REDACTED]")
    if not isinstance(replacement, str) or not replacement:
        raise ScanInputError(config_path, "redaction replacement must be a non-empty string")

    configured_value = redaction.get("fields", [])
    if not isinstance(configured_value, list) or not all(isinstance(item, str) for item in configured_value):
        raise ScanInputError(config_path, "redaction fields must be a list of strings")
    configured_fields = {item.lower() for item in configured_value}
    missing_configuration = sorted(SENSITIVE_FIELDS - configured_fields)

    leaks: list[str] = []
    for line_number, line in enumerate(read_text(log_path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScanInputError(
                log_path,
                f"invalid JSON log record at line {line_number}, column {error.colno}",
            ) from error
        record = require_mapping(record, log_path, f"log record at line {line_number}")
        for field in sorted(SENSITIVE_FIELDS):
            value = record.get(field)
            if value not in (None, "", replacement):
                leaks.append(f"line {line_number}:{field}")

    if enabled and not missing_configuration and not leaks:
        return []

    observations: list[str] = []
    if not enabled:
        observations.append("redaction is disabled")
    if missing_configuration:
        observations.append("redaction configuration omits " + ", ".join(missing_configuration))
    if leaks:
        observations.append("unredacted sensitive fields occur at " + ", ".join(leaks))

    application = str(config.get("application", "synthetic-measure-runner"))
    return [
        Finding(
            rule_id=RULE_ID,
            title="Synthetic member fields are not fully redacted from logs",
            severity="high",
            confidence=1.0,
            category="sensitive-log-redaction",
            target=application,
            expected="Sensitive fields are configured for redaction and contain no unredacted values in logs.",
            observed="; ".join(observations) + ".",
            evidence=(
                EvidenceReference(
                    context.display_path(config_path),
                    "Redaction enabled flag, field allowlist, and replacement marker.",
                ),
                EvidenceReference(
                    context.display_path(log_path),
                    "Sensitive field names and line locations only; field values are not copied into findings.",
                ),
            ),
        )
    ]
