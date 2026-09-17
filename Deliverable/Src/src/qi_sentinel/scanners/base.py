"""Shared scanner context and input-loading helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml


class ScanInputError(ValueError):
    """An input is missing, unreadable, or structurally invalid."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


@dataclass(frozen=True, slots=True)
class ScanContext:
    """Resolved paths supplied to every deterministic scanner."""

    project_root: Path
    platform_path: Path
    specification_path: Path

    @classmethod
    def from_root(
        cls,
        root: Path,
        *,
        platform_path: Path | None = None,
        specification_path: Path | None = None,
    ) -> "ScanContext":
        root = root.resolve()
        platform = platform_path or Path("mock-platform")
        specification = specification_path or Path("specs/synthetic-2026")
        if not platform.is_absolute():
            platform = root / platform
        if not specification.is_absolute():
            specification = root / specification
        return cls(root, platform.resolve(), specification.resolve())

    def display_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.project_root).as_posix()
        except ValueError:
            return path.resolve().as_posix()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ScanInputError(path, "required file is missing") from error
    except UnicodeDecodeError as error:
        raise ScanInputError(path, "file is not valid UTF-8") from error
    except OSError as error:
        raise ScanInputError(path, f"file could not be read: {error}") from error


def load_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as error:
        raise ScanInputError(path, f"invalid JSON at line {error.lineno}, column {error.colno}") from error


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(read_text(path))
    except yaml.YAMLError as error:
        raise ScanInputError(path, f"invalid YAML: {error}") from error


def require_mapping(value: Any, path: Path, label: str = "document") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScanInputError(path, f"{label} must be a mapping")
    return value


def require_list(value: Any, path: Path, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScanInputError(path, f"{label} must be a list")
    return value
