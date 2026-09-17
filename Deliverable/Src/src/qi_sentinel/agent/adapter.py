"""Official Codex SDK adapter with deterministic validation and fallback."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Protocol

from qi_sentinel.agent.context import build_analysis_context
from qi_sentinel.agent.schema import (
    AnalysisOutput,
    AnalysisValidationError,
    analysis_output_schema,
)
from qi_sentinel.models import Finding


class AnalysisUnavailableError(RuntimeError):
    """Raised when the external analysis service cannot return a response."""


class AnalysisBackend(Protocol):
    """Narrow seam used to exercise validation without a live model."""

    name: str

    def run(self, prompt: str, output_schema: dict[str, object]) -> str:
        """Return one structured JSON response."""


@dataclass(frozen=True, slots=True)
class AnalysisEnvelope:
    status: str
    provider: str
    analysis: AnalysisOutput
    prompt_sha256: str
    input_sha256: str
    response_sha256: str
    error_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "provider": self.provider,
            "analysis": self.analysis.to_dict(),
            "prompt_sha256": self.prompt_sha256,
            "input_sha256": self.input_sha256,
            "response_sha256": self.response_sha256,
            "error_code": self.error_code,
        }


@dataclass(slots=True)
class CodexSdkBackend:
    """Synchronous adapter for the pinned official Python SDK."""

    root: Path
    model: str | None = None
    name: str = "openai-codex"

    def run(self, prompt: str, output_schema: dict[str, object]) -> str:
        # SDK imports intentionally remain inside qi_sentinel.agent.
        try:
            from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox
        except ImportError as error:
            raise AnalysisUnavailableError("codex_sdk_unavailable") from error

        try:
            config = CodexConfig(cwd=str(self.root.resolve()))
            with Codex(config) as codex:
                thread = codex.thread_start(
                    approval_mode=ApprovalMode.auto_review,
                    cwd=str(self.root.resolve()),
                    ephemeral=True,
                    model=self.model,
                    sandbox=Sandbox.read_only,
                )
                result = thread.run(
                    prompt,
                    approval_mode=ApprovalMode.auto_review,
                    output_schema=output_schema,
                    sandbox=Sandbox.read_only,
                )
        except Exception as error:  # SDK transports expose several versioned subclasses.
            raise AnalysisUnavailableError("codex_service_unavailable") from error

        if result.error is not None or not result.final_response:
            raise AnalysisUnavailableError("codex_response_unavailable")
        return result.final_response


def analyze_semantic_finding(
    *,
    root: Path,
    finding: Finding,
    backend: AnalysisBackend,
) -> AnalysisEnvelope:
    """Enrich a semantic finding while keeping all decisions in code."""

    context = build_analysis_context(root, finding)
    raw_response = backend.run(context.prompt, analysis_output_schema(context.allowed_sources))
    analysis = AnalysisOutput.from_json(
        raw_response,
        allowed_sources=context.allowed_sources,
        allowed_patch_path=context.allowed_patch_path,
    )
    return AnalysisEnvelope(
        status="completed",
        provider=backend.name,
        analysis=analysis,
        prompt_sha256=context.prompt_sha256,
        input_sha256=context.input_sha256,
        response_sha256=_sha256(raw_response),
    )


def analyze_semantic_finding_with_fallback(
    *,
    root: Path,
    finding: Finding,
    backend: AnalysisBackend,
) -> AnalysisEnvelope:
    """Return an explicit deterministic fallback only for service unavailability."""

    try:
        return analyze_semantic_finding(root=root, finding=finding, backend=backend)
    except AnalysisUnavailableError:
        context = build_analysis_context(root, finding)
        fallback = _fallback_analysis(finding)
        serialized = json.dumps(fallback.to_dict(), ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        return AnalysisEnvelope(
            status="fallback",
            provider="deterministic-fallback",
            analysis=fallback,
            prompt_sha256=context.prompt_sha256,
            input_sha256=context.input_sha256,
            response_sha256=_sha256(serialized),
            error_code="codex_unavailable",
        )


def _fallback_analysis(finding: Finding) -> AnalysisOutput:
    spec_source = next(
        (item.path for item in finding.evidence if item.path.startswith("specs/")),
        f"finding:{finding.rule_id}",
    )
    repository_source = next(
        (item.path for item in finding.evidence if item.path.startswith("mock-platform/")),
        f"finding:{finding.rule_id}",
    )
    return AnalysisOutput.from_mapping(
        {
            "rule_id": "QI-SEM-001",
            "disposition": "escalate",
            "summary": f"The deterministic scanner identified semantic drift for {finding.target}; Codex analysis was unavailable.",
            "expected": [{"statement": finding.expected, "source": spec_source}],
            "observed": [{"statement": finding.observed, "source": repository_source}],
            "root_cause": {
                "statement": "The implementation differs from the approved synthetic specification; a human must confirm why.",
                "basis": "inference",
            },
            "impact": "The synthetic measure result may differ from the approved definition.",
            "recommended_owner": "quality-analytics",
            "recommended_next_action": "Review the cited specification and implementation before preparing any change.",
            "proposed_patch": None,
            "unavailable_facts": [
                "Codex root-cause analysis was unavailable.",
                "The change history and approval history were not supplied.",
            ],
        },
        allowed_sources=frozenset({spec_source, repository_source, f"finding:{finding.rule_id}"}),
        allowed_patch_path="mock-platform/measures/cbp/cbp_rate.sql",
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
