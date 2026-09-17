"""Deterministic scanner orchestration."""

from __future__ import annotations

from collections.abc import Callable

from qi_sentinel.models import Finding, ordered_findings
from qi_sentinel.scanners import lineage, logging, masking, semantics
from qi_sentinel.scanners.base import ScanContext, ScanInputError

Scanner = Callable[[ScanContext], list[Finding]]

SCANNERS: tuple[Scanner, ...] = (
    masking.scan,
    logging.scan,
    semantics.scan,
    lineage.scan,
)


def scan_platform(context: ScanContext) -> tuple[Finding, ...]:
    """Run every Phase 2 scanner in a fixed order and canonicalize output."""

    findings: list[Finding] = []
    for scanner in SCANNERS:
        findings.extend(scanner(context))
    return ordered_findings(findings)


__all__ = ["ScanContext", "ScanInputError", "scan_platform"]
