"""Deterministic scanner for synthetic measure-semantic drift."""

from __future__ import annotations

import re

from qi_sentinel.models import EvidenceReference, Finding
from qi_sentinel.scanners.base import (
    ScanContext,
    ScanInputError,
    load_json,
    load_yaml,
    read_text,
    require_list,
    require_mapping,
)

RULE_ID = "QI-SEM-001"
VALUE_SET_PATTERN = re.compile(
    r"synthetic_value_set\(\s*['\"](?P<id>[^'\"]+)['\"]\s*,\s*['\"](?P<version>[^'\"]+)['\"]\s*\)",
    flags=re.IGNORECASE,
)
EXCLUSION_PATTERN = re.compile(
    r"exclusion_reason\s+NOT\s+IN\s*\((?P<values>.*?)\)",
    flags=re.IGNORECASE | re.DOTALL,
)
QUOTED_VALUE_PATTERN = re.compile(r"['\"](?P<value>[^'\"]+)['\"]")


def scan(context: ScanContext) -> list[Finding]:
    spec_path = context.specification_path / "cbp.yml"
    registry_path = context.specification_path / "value_sets.json"
    sql_path = context.platform_path / "measures" / "cbp" / "cbp_rate.sql"

    spec = require_mapping(load_yaml(spec_path), spec_path)
    population = require_mapping(spec.get("population"), spec_path, "population")
    value_set = require_mapping(population.get("value_set"), spec_path, "population.value_set")
    expected_id = _required_string(value_set, "id", spec_path)
    expected_version = _required_string(value_set, "version", spec_path)

    exclusion_value = population.get("denominator_exclusions")
    exclusions = require_list(exclusion_value, spec_path, "population.denominator_exclusions")
    if not exclusions or not all(isinstance(item, str) and item for item in exclusions):
        raise ScanInputError(spec_path, "denominator exclusions must contain non-empty strings")
    expected_exclusions = {item.upper() for item in exclusions}

    registry = require_mapping(load_json(registry_path), registry_path)
    entries = require_list(registry.get("value_sets"), registry_path, "value_sets")
    approved_versions: dict[str, str] = {}
    for index, entry in enumerate(entries):
        item = require_mapping(entry, registry_path, f"value_sets[{index}]")
        identifier = _required_string(item, "id", registry_path)
        version = _required_string(item, "version", registry_path)
        approved_versions[identifier] = version
    if approved_versions.get(expected_id) != expected_version:
        raise ScanInputError(
            registry_path,
            f"registry does not approve {expected_id} version {expected_version}",
        )

    sql = read_text(sql_path)
    reference = VALUE_SET_PATTERN.search(sql)
    exclusion_clause = EXCLUSION_PATTERN.search(sql)
    observations: list[str] = []

    if reference is None:
        observations.append("no synthetic value-set reference was found")
    else:
        actual_id = reference.group("id")
        actual_version = reference.group("version")
        if actual_id != expected_id:
            observations.append(f"value-set ID is {actual_id}, expected {expected_id}")
        if actual_version != expected_version:
            observations.append(f"value-set version is {actual_version}, expected {expected_version}")

    if exclusion_clause is None:
        observations.append("no denominator exclusion clause was found")
    else:
        actual_exclusions = {
            match.group("value").upper()
            for match in QUOTED_VALUE_PATTERN.finditer(exclusion_clause.group("values"))
        }
        missing = sorted(expected_exclusions - actual_exclusions)
        unexpected = sorted(actual_exclusions - expected_exclusions)
        if missing:
            observations.append("missing exclusions: " + ", ".join(missing))
        if unexpected:
            observations.append("unexpected exclusions: " + ", ".join(unexpected))

    if not observations:
        return []

    measure_id = _required_string(spec, "measure_id", spec_path).upper()
    return [
        Finding(
            rule_id=RULE_ID,
            title="Synthetic measure logic differs from the approved specification",
            severity="high",
            confidence=1.0,
            category="measure-semantics",
            target=measure_id,
            expected=(
                f"{measure_id} uses {expected_id} version {expected_version} and denominator exclusions "
                + ", ".join(sorted(expected_exclusions))
                + "."
            ),
            observed="; ".join(observations) + ".",
            evidence=(
                EvidenceReference(
                    context.display_path(spec_path),
                    f"Approved synthetic population controls for {measure_id}.",
                ),
                EvidenceReference(
                    context.display_path(registry_path),
                    f"Approved version registry entry for {expected_id}.",
                ),
                EvidenceReference(
                    context.display_path(sql_path),
                    f"Implemented value-set reference and denominator exclusions for {measure_id}.",
                ),
            ),
        )
    ]


def _required_string(mapping: dict[str, object], key: str, path: object) -> str:
    value = mapping.get(key)
    if value is None:
        raise ScanInputError(path, f"field {key!r} is required")
    normalized = str(value).strip()
    if not normalized:
        raise ScanInputError(path, f"field {key!r} must not be empty")
    return normalized
