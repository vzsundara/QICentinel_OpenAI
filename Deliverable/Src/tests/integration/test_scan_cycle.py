"""Integration checks for the complete deterministic scan stage."""

from __future__ import annotations

from pathlib import Path

from qi_sentinel.models import findings_json
from qi_sentinel.scanners import ScanContext, scan_platform

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE = PROJECT_ROOT / "tests" / "fixtures" / "baseline" / "mock-platform"


def test_seeded_platform_produces_exactly_four_findings() -> None:
    findings = scan_platform(ScanContext.from_root(PROJECT_ROOT))

    assert [finding.rule_id for finding in findings] == [
        "QI-LIN-001",
        "QI-LOG-001",
        "QI-MASK-001",
        "QI-SEM-001",
    ]
    assert len({finding.fingerprint for finding in findings}) == 4


def test_clean_baseline_produces_no_findings() -> None:
    context = ScanContext.from_root(PROJECT_ROOT, platform_path=BASELINE)

    assert scan_platform(context) == ()


def test_repeated_scans_are_byte_for_byte_deterministic() -> None:
    context = ScanContext.from_root(PROJECT_ROOT)

    first = findings_json(scan_platform(context))
    second = findings_json(scan_platform(context))

    assert first == second
