"""Command-line shells for the QI Sentinel proof of concept."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from qi_sentinel import __version__
from qi_sentinel.models import findings_json
from qi_sentinel.policy import PolicyConfigError, run_action_cycle
from qi_sentinel.scanners import ScanContext, ScanInputError, scan_platform

EXPECTED_RULE_IDS = {
    "QI-LIN-001",
    "QI-LOG-001",
    "QI-MASK-001",
    "QI-SEM-001",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="QI Sentinel synthetic compliance proof of concept.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser(
        "seed",
        help="Validate the checked-in synthetic Phase 1 seed catalog.",
    )
    seed_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root containing tests/fixtures/seeds.json.",
    )
    seed_parser.set_defaults(handler=_seed)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Run the four deterministic scanners.",
    )
    scan_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root used to resolve input and output paths.",
    )
    scan_parser.add_argument(
        "--platform",
        type=Path,
        default=Path("mock-platform"),
        help="Seeded or baseline platform directory, relative to --root unless absolute.",
    )
    scan_parser.add_argument(
        "--specification",
        type=Path,
        default=Path("specs/synthetic-2026"),
        help="Specification snapshot directory, relative to --root unless absolute.",
    )
    scan_parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path, relative to --root unless absolute.",
    )
    scan_parser.add_argument(
        "--no-remediate",
        action="store_true",
        help="Retained for the future scan-only workflow contract.",
    )
    scan_parser.set_defaults(handler=_scan)

    remediate_parser = subparsers.add_parser(
        "remediate",
        help="Run the local policy gate and prepare reviewable actions.",
    )
    remediate_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root containing config/policy.yml and mock-platform/.",
    )
    remediate_parser.add_argument(
        "--mode",
        choices=("enforce", "observe"),
        help="Override the versioned policy mode for this run.",
    )
    remediate_parser.add_argument(
        "--state",
        type=Path,
        default=Path("artifacts/phase4/action-state.json"),
        help="Local idempotency state path, relative to --root unless absolute.",
    )
    remediate_parser.add_argument(
        "--output",
        type=Path,
        help="Optional canonical result path, relative to --root unless absolute.",
    )
    remediate_parser.set_defaults(handler=_remediate)

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify an evidence pack (available in Phase 5).",
    )
    verify_parser.add_argument(
        "artifact",
        nargs="?",
        type=Path,
        help="Evidence directory or canonical evidence.json file.",
    )
    verify_parser.set_defaults(handler=_not_implemented, phase="Phase 5")

    return parser


def _seed(args: argparse.Namespace) -> int:
    """Validate seed metadata and its referenced Phase 1 fixture files."""

    root = args.root.resolve()
    catalog_path = root / "tests" / "fixtures" / "seeds.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Seed catalog not found: {catalog_path}")
        return 2
    except json.JSONDecodeError as error:
        print(f"Seed catalog is not valid JSON: {error}")
        return 2

    seeds = catalog.get("seeds")
    if not isinstance(seeds, list):
        print("Seed catalog must contain a 'seeds' list.")
        return 2

    rule_ids = {seed.get("rule_id") for seed in seeds if isinstance(seed, dict)}
    if rule_ids != EXPECTED_RULE_IDS:
        observed = sorted(str(item) for item in rule_ids)
        print(
            "Seed catalog rule IDs do not match the Phase 1 contract: "
            f"expected {sorted(EXPECTED_RULE_IDS)}, observed {observed}"
        )
        return 2

    missing: list[str] = []
    for seed in seeds:
        for field in ("seeded_files", "baseline_files"):
            paths = seed.get(field, [])
            if not isinstance(paths, list):
                print(f"{seed['rule_id']} field '{field}' must be a list.")
                return 2
            for relative_path in paths:
                if not isinstance(relative_path, str) or not (root / relative_path).is_file():
                    missing.append(str(relative_path))

    if missing:
        print("Seed catalog references missing files:")
        for relative_path in sorted(set(missing)):
            print(f"  - {relative_path}")
        return 2

    print(f"Synthetic seed catalog: valid ({len(seeds)} seeds)")
    for seed in sorted(seeds, key=lambda item: item["rule_id"]):
        print(f"  {seed['rule_id']}: {seed['expected_disposition']}")
    print("Run 'sentinel scan' to execute deterministic detection.")
    return 0


def _scan(args: argparse.Namespace) -> int:
    """Run deterministic scanners and emit canonical findings JSON."""

    root = args.root.resolve()
    context = ScanContext.from_root(
        root,
        platform_path=args.platform,
        specification_path=args.specification,
    )
    try:
        output = findings_json(scan_platform(context))
    except (ScanInputError, ValueError) as error:
        print(f"Scan failed: {error}", file=sys.stderr)
        return 2

    if args.output is None:
        print(output, end="")
        return 0

    output_path = args.output
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8", newline="\n")
    print(f"Wrote deterministic findings to {context.display_path(output_path)}")
    return 0


def _remediate(args: argparse.Namespace) -> int:
    """Run the deterministic policy and local action workflow."""

    root = args.root.resolve()
    try:
        result = run_action_cycle(
            root,
            mode=args.mode,
            state_path=args.state,
        )
    except (PolicyConfigError, ScanInputError, ValueError) as error:
        print(f"Remediation failed: {error}", file=sys.stderr)
        return 2

    output = result.to_json()
    if args.output is None:
        print(output, end="")
        return 0

    try:
        output_path = _path_within_root(root, args.output)
    except ValueError as error:
        print(f"Remediation failed: {error}", file=sys.stderr)
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8", newline="\n")
    print(f"Wrote Phase 4 action result to {output_path.relative_to(root).as_posix()}")
    return 0


def _path_within_root(root: Path, path: Path) -> Path:
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("Output path must remain within the project root.") from error
    return resolved


def _not_implemented(args: argparse.Namespace) -> int:
    """Fail safely when a later-phase command is invoked."""

    print(f"'{args.command}' is a command shell; implementation begins in {args.phase}.")
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run the QI Sentinel CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))
