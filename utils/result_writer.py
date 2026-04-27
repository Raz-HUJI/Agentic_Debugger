from __future__ import annotations

import datetime
import json
import logging
import pathlib
from typing import Optional

from Debugger.ModularDebuggerFlow import DebuggerState

log = logging.getLogger("agent_fix.result")


def write_result(
    path: str,
    command: str,
    target_dir: str,
    state: DebuggerState,
    rubric_name: Optional[str] = None,
) -> None:
    """Serialise the final DebuggerState to a structured JSON file.

    The output is self-contained so downstream automation (CI reporters,
    dashboards, etc.) can consume it without re-running the pipeline.
    """
    out = pathlib.Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "command": command,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_dir": target_dir,
        "rubric": rubric_name,
        "approved": state.approved,
        "analysis": state.analysis_output,
        "proposed_fix": state.proposed_fix,
        "judgment": (
            state.judgment_output.model_dump() if state.judgment_output else None
        ),
        "exit_code": 0 if state.approved else 10,
    }

    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Results written to '%s'", out.resolve())
