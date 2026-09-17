"""Focused tests for each deterministic scanner."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from qi_sentinel.scanners import lineage, logging, masking, semantics
from qi_sentinel.scanners.base import ScanContext, ScanInputError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPECIFICATION = PROJECT_ROOT / "specs" / "synthetic-2026"
BASELINE = PROJECT_ROOT / "tests" / "fixtures" / "baseline" / "mock-platform"


def seeded_context() -> ScanContext:
    return ScanContext.from_root(PROJECT_ROOT)


def baseline_context() -> ScanContext:
    return ScanContext.from_root(PROJECT_ROOT, platform_path=BASELINE)


@pytest.mark.parametrize(
    ("scanner", "rule_id"),
    [
        (masking.scan, "QI-MASK-001"),
        (logging.scan, "QI-LOG-001"),
        (semantics.scan, "QI-SEM-001"),
        (lineage.scan, "QI-LIN-001"),
    ],
)
def test_scanner_finds_only_its_seed(scanner: object, rule_id: str) -> None:
    findings = scanner(seeded_context())  # type: ignore[operator]

    assert [finding.rule_id for finding in findings] == [rule_id]
    assert findings[0].confidence == 1.0
    assert findings[0].evidence


@pytest.mark.parametrize(
    "scanner",
    [masking.scan, logging.scan, semantics.scan, lineage.scan],
)
def test_scanner_reports_nothing_on_clean_baseline(scanner: object) -> None:
    assert scanner(baseline_context()) == []  # type: ignore[operator]


def test_masking_scanner_ignores_an_untagged_column(tmp_path: Path) -> None:
    context = copied_context(tmp_path, baseline=True)
    columns_path = context.platform_path / "snowflake" / "information_schema" / "columns.json"
    payload = json.loads(columns_path.read_text(encoding="utf-8"))
    payload["columns"][0]["tag"] = "PUBLIC"
    payload["columns"][0]["masking_policy"] = None
    columns_path.write_text(json.dumps(payload), encoding="utf-8")

    assert masking.scan(context) == []


@pytest.mark.parametrize(
    ("scanner", "relative_path", "malformed"),
    [
        (masking.scan, "snowflake/information_schema/columns.json", "{"),
        (logging.scan, "pipelines/logging.yml", "redaction: ["),
        (semantics.scan, "../specs/cbp.yml", "population: ["),
        (lineage.scan, "lineage/measures.json", "{"),
    ],
)
def test_malformed_input_fails_explicitly(
    tmp_path: Path,
    scanner: object,
    relative_path: str,
    malformed: str,
) -> None:
    context = copied_context(tmp_path)
    if relative_path.startswith("../specs/"):
        target = context.specification_path / Path(relative_path).name
    else:
        target = context.platform_path / relative_path
    target.write_text(malformed, encoding="utf-8")

    with pytest.raises(ScanInputError):
        scanner(context)  # type: ignore[operator]


def copied_context(tmp_path: Path, *, baseline: bool = False) -> ScanContext:
    source = BASELINE if baseline else PROJECT_ROOT / "mock-platform"
    platform = tmp_path / "mock-platform"
    specification = tmp_path / "specs"
    shutil.copytree(source, platform)
    shutil.copytree(SPECIFICATION, specification)
    return ScanContext.from_root(
        tmp_path,
        platform_path=platform,
        specification_path=specification,
    )
