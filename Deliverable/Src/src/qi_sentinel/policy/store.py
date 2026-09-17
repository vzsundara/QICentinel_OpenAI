"""Local idempotency store for review payloads and escalation records."""

from __future__ import annotations

import json
from pathlib import Path


class ActionStore:
    def __init__(self, root: Path, path: Path) -> None:
        self.root = root.resolve()
        self.path = path if path.is_absolute() else self.root / path
        self.path = self.path.resolve()
        try:
            self.path.relative_to(self.root)
        except ValueError as error:
            raise ValueError("Action state path must remain within the project root.") from error

    def update(
        self,
        pull_request: dict[str, object] | None,
        escalations: tuple[dict[str, object], ...],
    ) -> tuple[dict[str, object] | None, tuple[dict[str, object], ...]]:
        state = self._load()
        pull_requests = state["pull_requests"]
        escalation_records = state["escalations"]

        stored_pr: dict[str, object] | None = None
        if pull_request is not None:
            key = str(pull_request["local_record_id"])
            existing = pull_requests.get(key)
            revision = int(existing.get("revision", 0)) + 1 if isinstance(existing, dict) else 1
            if isinstance(existing, dict) and pull_request.get("patch") is None:
                pull_request["patch"] = existing.get("patch")
            stored_pr = {**pull_request, "revision": revision}
            pull_requests[key] = stored_pr

        stored_escalations: list[dict[str, object]] = []
        for escalation in escalations:
            key = str(escalation["finding_fingerprint"])
            existing = escalation_records.get(key)
            revision = int(existing.get("revision", 0)) + 1 if isinstance(existing, dict) else 1
            stored = {**escalation, "revision": revision}
            escalation_records[key] = stored
            stored_escalations.append(stored)

        self._write(state)
        return stored_pr, tuple(sorted(stored_escalations, key=lambda item: str(item["rule_id"])))

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {"schema_version": 1, "pull_requests": {}, "escalations": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError("Action state is unreadable or invalid JSON.") from error
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise ValueError("Action state schema_version must equal 1.")
        if not isinstance(value.get("pull_requests"), dict) or not isinstance(value.get("escalations"), dict):
            raise ValueError("Action state record collections must be mappings.")
        return value

    def _write(self, state: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(self.path)
