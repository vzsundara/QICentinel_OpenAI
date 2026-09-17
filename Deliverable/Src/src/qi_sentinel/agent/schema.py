"""Strict schema and trust-boundary validation for Codex analysis output."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

RULE_ID = "QI-SEM-001"
DISPOSITION = "escalate"
OWNER = "quality-analytics"

ANALYSIS_OUTPUT_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "rule_id",
        "disposition",
        "summary",
        "expected",
        "observed",
        "root_cause",
        "impact",
        "recommended_owner",
        "recommended_next_action",
        "proposed_patch",
        "unavailable_facts",
    ],
    "properties": {
        "rule_id": {"type": "string", "const": RULE_ID},
        "disposition": {"type": "string", "const": DISPOSITION},
        "summary": {"type": "string", "minLength": 1},
        "expected": {"$ref": "#/$defs/statements"},
        "observed": {"$ref": "#/$defs/statements"},
        "root_cause": {
            "type": "object",
            "additionalProperties": False,
            "required": ["statement", "basis"],
            "properties": {
                "statement": {"type": "string", "minLength": 1},
                "basis": {"type": "string", "enum": ["evidence", "inference"]},
            },
        },
        "impact": {"type": "string", "minLength": 1},
        "recommended_owner": {"type": "string", "const": OWNER},
        "recommended_next_action": {"type": "string", "minLength": 1},
        "proposed_patch": {"type": ["string", "null"]},
        "unavailable_facts": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
    },
    "$defs": {
        "statements": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["statement", "source"],
                "properties": {
                    "statement": {"type": "string", "minLength": 1},
                    "source": {"type": "string", "minLength": 1},
                },
            },
        }
    },
}

_FORBIDDEN_ACTION = re.compile(
    r"\b(?:bypass(?:ing)?\s+policy|merge(?:d|s|ing)?|deploy(?:ed|s|ing)?|"
    r"access(?:ed|es|ing)?\s+production|auto[- ]?apply|disable\s+(?:a\s+)?control)\b",
    flags=re.IGNORECASE,
)
_INVENTED_POPULATION = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s*(?:members?|patients?|people|records?|percent|%)\b",
    flags=re.IGNORECASE,
)


class AnalysisValidationError(ValueError):
    """Raised when model output crosses a schema or policy boundary."""


def analysis_output_schema(allowed_sources: frozenset[str]) -> dict[str, object]:
    """Bind the static response schema to this invocation's evidence allowlist."""

    schema = deepcopy(ANALYSIS_OUTPUT_SCHEMA)
    source_schema = schema["$defs"]["statements"]["items"]["properties"]["source"]
    source_schema["enum"] = sorted(allowed_sources)
    return schema


@dataclass(frozen=True, slots=True)
class SourcedStatement:
    statement: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return {"statement": self.statement, "source": self.source}


@dataclass(frozen=True, slots=True)
class RootCause:
    statement: str
    basis: str

    def to_dict(self) -> dict[str, str]:
        return {"statement": self.statement, "basis": self.basis}


@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    rule_id: str
    disposition: str
    summary: str
    expected: tuple[SourcedStatement, ...]
    observed: tuple[SourcedStatement, ...]
    root_cause: RootCause
    impact: str
    recommended_owner: str
    recommended_next_action: str
    proposed_patch: str | None
    unavailable_facts: tuple[str, ...]

    @classmethod
    def from_json(
        cls,
        raw: str,
        *,
        allowed_sources: frozenset[str],
        allowed_patch_path: str,
    ) -> "AnalysisOutput":
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise AnalysisValidationError("Analysis response is not valid JSON.") from error
        if not isinstance(value, dict):
            raise AnalysisValidationError("Analysis response must be a JSON object.")
        return cls.from_mapping(
            value,
            allowed_sources=allowed_sources,
            allowed_patch_path=allowed_patch_path,
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        allowed_sources: frozenset[str],
        allowed_patch_path: str,
    ) -> "AnalysisOutput":
        expected_keys = {
            "rule_id",
            "disposition",
            "summary",
            "expected",
            "observed",
            "root_cause",
            "impact",
            "recommended_owner",
            "recommended_next_action",
            "proposed_patch",
            "unavailable_facts",
        }
        _require_exact_keys(value, expected_keys, "analysis")

        rule_id = _required_string(value, "rule_id")
        disposition = _required_string(value, "disposition")
        owner = _required_string(value, "recommended_owner")
        if rule_id != RULE_ID:
            raise AnalysisValidationError(f"Model changed or invented rule ID: {rule_id!r}.")
        if disposition != DISPOSITION:
            raise AnalysisValidationError("Model changed the deterministic disposition.")
        if owner != OWNER:
            raise AnalysisValidationError("Model selected an unsupported owner.")

        expected = _sourced_statements(value.get("expected"), "expected", allowed_sources)
        observed = _sourced_statements(value.get("observed"), "observed", allowed_sources)
        root_cause_value = _required_mapping(value, "root_cause")
        _require_exact_keys(root_cause_value, {"statement", "basis"}, "root_cause")
        root_cause = RootCause(
            statement=_required_string(root_cause_value, "statement"),
            basis=_required_string(root_cause_value, "basis"),
        )
        if root_cause.basis not in {"evidence", "inference"}:
            raise AnalysisValidationError("Root-cause basis must be evidence or inference.")

        summary = _required_string(value, "summary")
        impact = _required_string(value, "impact")
        next_action = _required_string(value, "recommended_next_action")
        for text in (summary, root_cause.statement, impact, next_action):
            if _FORBIDDEN_ACTION.search(text):
                raise AnalysisValidationError("Analysis recommends an unsupported action.")
        if _INVENTED_POPULATION.search(impact):
            raise AnalysisValidationError("Analysis invents a population count or percentage.")

        patch = value.get("proposed_patch")
        if patch is not None:
            if not isinstance(patch, str) or not patch.strip():
                raise AnalysisValidationError("proposed_patch must be a non-empty string or null.")
            _validate_patch(patch, allowed_patch_path)

        unavailable_value = value.get("unavailable_facts")
        if not isinstance(unavailable_value, list):
            raise AnalysisValidationError("unavailable_facts must be an array.")
        unavailable = tuple(_non_empty_string(item, "unavailable_facts item") for item in unavailable_value)

        return cls(
            rule_id=rule_id,
            disposition=disposition,
            summary=summary,
            expected=expected,
            observed=observed,
            root_cause=root_cause,
            impact=impact,
            recommended_owner=owner,
            recommended_next_action=next_action,
            proposed_patch=patch,
            unavailable_facts=unavailable,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "disposition": self.disposition,
            "summary": self.summary,
            "expected": [item.to_dict() for item in self.expected],
            "observed": [item.to_dict() for item in self.observed],
            "root_cause": self.root_cause.to_dict(),
            "impact": self.impact,
            "recommended_owner": self.recommended_owner,
            "recommended_next_action": self.recommended_next_action,
            "proposed_patch": self.proposed_patch,
            "unavailable_facts": list(self.unavailable_facts),
        }


def _sourced_statements(
    value: object,
    field: str,
    allowed_sources: frozenset[str],
) -> tuple[SourcedStatement, ...]:
    if not isinstance(value, list) or not value:
        raise AnalysisValidationError(f"{field} must be a non-empty array.")
    result: list[SourcedStatement] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise AnalysisValidationError(f"{field}[{index}] must be an object.")
        _require_exact_keys(item, {"statement", "source"}, f"{field}[{index}]")
        source = _required_string(item, "source")
        if source not in allowed_sources:
            raise AnalysisValidationError(f"Analysis cites an unprovided source: {source!r}.")
        result.append(SourcedStatement(_required_string(item, "statement"), source))
    return tuple(result)


def _validate_patch(patch: str, allowed_path: str) -> None:
    headers = [line[4:].strip() for line in patch.splitlines() if line.startswith(("--- ", "+++ "))]
    if len(headers) != 2:
        raise AnalysisValidationError("Proposed patch must be a single-file unified diff.")
    normalized = {header.removeprefix("a/").removeprefix("b/") for header in headers}
    if normalized != {allowed_path}:
        raise AnalysisValidationError("Proposed patch targets a path outside the allowlist.")


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        raise AnalysisValidationError(f"{label} keys do not match schema; missing={missing}, unknown={unknown}.")


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise AnalysisValidationError(f"{key} must be an object.")
    return item


def _required_string(value: Mapping[str, Any], key: str) -> str:
    return _non_empty_string(value.get(key), key)


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AnalysisValidationError(f"{label} must be a non-empty string.")
    return value.strip()
