"""Phase 1 smoke tests for the command shells."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from qi_sentinel.cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CliSmokeTests(unittest.TestCase):
    def test_seed_validates_checked_in_catalog(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["seed", "--root", str(PROJECT_ROOT)])

        self.assertEqual(status, 0)
        self.assertIn("valid (4 seeds)", output.getvalue())
        self.assertIn("sentinel scan", output.getvalue())

    def test_verify_requires_an_artifact(self) -> None:
        output = io.StringIO()
        with patch("sys.stderr", output):
            status = main(["verify", "--root", str(PROJECT_ROOT)])

        self.assertEqual(status, 2)
        self.assertIn("path is required", output.getvalue())

    def test_verify_reports_valid_pack(self) -> None:
        verification = SimpleNamespace(
            valid=True,
            evidence_path=PROJECT_ROOT / "artifacts/demo/evidence.json",
            checked_source_count=12,
            errors=(),
        )
        output = io.StringIO()
        with patch("qi_sentinel.cli.verify_evidence_pack", return_value=verification):
            with redirect_stdout(output):
                status = main(["verify", "artifacts/demo", "--root", str(PROJECT_ROOT)])

        self.assertEqual(status, 0)
        self.assertIn("Evidence verified", output.getvalue())

    def test_evidence_command_generates_observe_pack(self) -> None:
        pack = SimpleNamespace(directory=PROJECT_ROOT / "artifacts/demo")
        output = io.StringIO()
        with patch("qi_sentinel.cli.run_action_cycle", return_value=object()) as cycle:
            with patch("qi_sentinel.cli.generate_evidence_pack", return_value=pack) as generate:
                with redirect_stdout(output):
                    status = main(
                        ["evidence", "--root", str(PROJECT_ROOT), "--run-id", "demo"]
                    )

        self.assertEqual(status, 0)
        self.assertEqual(cycle.call_args.kwargs["mode"], "observe")
        self.assertEqual(generate.call_args.kwargs["run_id"], "demo")
        self.assertIn("artifacts/demo", output.getvalue())

    def test_remediate_emits_action_cycle_json(self) -> None:
        class FakeResult:
            def to_json(self) -> str:
                return '{"mode":"observe"}\n'

        output = io.StringIO()
        with patch("qi_sentinel.cli.run_action_cycle", return_value=FakeResult()) as cycle:
            with redirect_stdout(output):
                status = main(["remediate", "--root", str(PROJECT_ROOT), "--mode", "observe"])

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), {"mode": "observe"})
        self.assertEqual(cycle.call_args.kwargs["mode"], "observe")

    def test_scan_emits_canonical_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["scan", "--root", str(PROJECT_ROOT)])

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["finding_count"], 4)
        self.assertEqual(
            [item["rule_id"] for item in payload["findings"]],
            ["QI-LIN-001", "QI-LOG-001", "QI-MASK-001", "QI-SEM-001"],
        )


if __name__ == "__main__":
    unittest.main()
