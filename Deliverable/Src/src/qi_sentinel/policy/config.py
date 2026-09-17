"""Strict loader for the versioned QI Sentinel policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

REQUIRED_GATE_CHECKS = (
    "rule_allows_auto_fix",
    "does_not_change_measure_population",
    "confidence_meets_threshold",
    "files_and_commands_are_allowlisted",
    "required_tests_pass",
    "submitted_for_human_review",
)


class PolicyConfigError(ValueError):
    """Raised when policy is missing, malformed, or weakens a hard boundary."""


@dataclass(frozen=True, slots=True)
class RulePolicy:
    rule_id: str
    category: str
    severity: str
    auto_fix_allowed: bool
    owner: str


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    version: int
    mode: str
    minimum_confidence: float
    default_auto_fix_allowed: bool
    rules: Mapping[str, RulePolicy]
    required_checks: tuple[str, ...]
    never_auto_apply: frozenset[str]
    allowed_files: frozenset[str]
    allowed_commands: frozenset[str]
    merge: str
    require_human_review: bool

    @classmethod
    def load(cls, path: Path) -> "PolicyConfig":
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise PolicyConfigError(f"Policy file not found: {path}.") from error
        except (OSError, UnicodeError, yaml.YAMLError) as error:
            raise PolicyConfigError(f"Policy file could not be loaded safely: {path}.") from error
        root = _mapping(payload, "policy")

        version = root.get("version")
        if version != 1:
            raise PolicyConfigError("Policy version must equal 1.")
        mode = _string(root, "mode")
        if mode not in {"enforce", "observe"}:
            raise PolicyConfigError("Policy mode must be enforce or observe.")

        defaults = _mapping(root.get("defaults"), "defaults")
        minimum_confidence = defaults.get("minimum_confidence")
        if not isinstance(minimum_confidence, (int, float)) or isinstance(minimum_confidence, bool):
            raise PolicyConfigError("defaults.minimum_confidence must be numeric.")
        minimum_confidence = float(minimum_confidence)
        if not 0.0 <= minimum_confidence <= 1.0:
            raise PolicyConfigError("defaults.minimum_confidence must be between 0 and 1.")
        default_auto_fix = defaults.get("auto_fix_allowed")
        if not isinstance(default_auto_fix, bool):
            raise PolicyConfigError("defaults.auto_fix_allowed must be boolean.")

        rules_value = _mapping(root.get("rules"), "rules")
        rules: dict[str, RulePolicy] = {}
        for rule_id, value in rules_value.items():
            if not isinstance(rule_id, str):
                raise PolicyConfigError("Policy rule IDs must be strings.")
            item = _mapping(value, f"rules.{rule_id}")
            auto_fix_allowed = item.get("auto_fix_allowed", default_auto_fix)
            if not isinstance(auto_fix_allowed, bool):
                raise PolicyConfigError(f"rules.{rule_id}.auto_fix_allowed must be boolean.")
            rules[rule_id] = RulePolicy(
                rule_id=rule_id,
                category=_string(item, "category", f"rules.{rule_id}"),
                severity=_string(item, "severity", f"rules.{rule_id}"),
                auto_fix_allowed=auto_fix_allowed,
                owner=_string(item, "owner", f"rules.{rule_id}"),
            )

        gate = _mapping(root.get("gate"), "gate")
        checks = _string_tuple(gate.get("require_all"), "gate.require_all")
        if checks != REQUIRED_GATE_CHECKS:
            raise PolicyConfigError("gate.require_all must contain the six required checks in canonical order.")
        hard_floor = frozenset(_string_tuple(gate.get("never_auto_apply"), "gate.never_auto_apply"))
        required_floor = {"measure-semantics", "evidence-attestation", "access-grant-widening"}
        if not required_floor.issubset(hard_floor):
            raise PolicyConfigError("gate.never_auto_apply cannot weaken the required hard floor.")

        allowlists = _mapping(root.get("allowlists"), "allowlists")
        allowed_files = frozenset(_string_tuple(allowlists.get("files"), "allowlists.files"))
        allowed_commands = frozenset(_string_tuple(allowlists.get("commands"), "allowlists.commands"))

        pull_requests = _mapping(root.get("pull_requests"), "pull_requests")
        merge = _string(pull_requests, "merge", "pull_requests")
        require_human_review = pull_requests.get("require_human_review")
        if merge != "never":
            raise PolicyConfigError("pull_requests.merge must remain never.")
        if require_human_review is not True:
            raise PolicyConfigError("pull_requests.require_human_review must remain true.")

        return cls(
            version=version,
            mode=mode,
            minimum_confidence=minimum_confidence,
            default_auto_fix_allowed=default_auto_fix,
            rules=rules,
            required_checks=checks,
            never_auto_apply=hard_floor,
            allowed_files=allowed_files,
            allowed_commands=allowed_commands,
            merge=merge,
            require_human_review=require_human_review,
        )


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyConfigError(f"{label} must be a mapping.")
    return value


def _string(mapping: Mapping[str, object], key: str, prefix: str = "policy") -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PolicyConfigError(f"{prefix}.{key} must be a non-empty string.")
    return value.strip()


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise PolicyConfigError(f"{label} must be a non-empty list of strings.")
    result = tuple(item.strip() for item in value)
    if len(result) != len(set(result)):
        raise PolicyConfigError(f"{label} must not contain duplicates.")
    return result
