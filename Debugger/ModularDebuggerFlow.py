from __future__ import annotations

import logging
import pathlib
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from utils.rubric_loader import JudgmentOutput

log = logging.getLogger("agent_fix.flow")


class DebuggerState(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    # Context — populated by kickoff from inputs / filesystem scan
    target_dir: str = ""
    logs: list[str] = Field(default_factory=list)
    code_snippets: dict[str, str] = Field(default_factory=dict)

    # Written by BugFixerAgent (Researcher role)
    analysis_output: str = ""
    proposed_fix: str = ""

    # Written by CodeQualityJudge (Judge role)
    judgment: str = ""                          # JSON string of the full judgment
    judgment_output: Optional[JudgmentOutput] = None  # validated structured object
    approved: bool = False

    # Assembled by ModularDebuggerFlow after both agents run
    final_result: str = ""


class BaseAgent(ABC):
    @abstractmethod
    def run(self, state: DebuggerState) -> DebuggerState:
        """Execute the agent's task. Receives full state, returns updated state."""
        ...

    @property
    @abstractmethod
    def role(self) -> str:
        """Human-readable role label used for logging and introspection."""
        ...


class ModularDebuggerFlow:
    def __init__(self, fixer_agent: BaseAgent, judge_agent: BaseAgent) -> None:
        self._fixer = fixer_agent
        self._judge = judge_agent
        self.last_state: Optional[DebuggerState] = None

    def kickoff(self, inputs: dict) -> str:
        state = DebuggerState(target_dir=inputs.get("target_dir", ""))

        state = self._collect_context(state)

        log.info("Running agent | role='%s'", self._fixer.role)
        state = self._fixer.run(state)

        log.info("Running agent | role='%s'", self._judge.role)
        state = self._judge.run(state)

        state = self._assemble_result(state)
        self.last_state = state
        return state.final_result

    # ------------------------------------------------------------------
    # Private helpers — infrastructure concerns, not agent concerns
    # ------------------------------------------------------------------

    def _collect_context(self, state: DebuggerState) -> DebuggerState:
        target = pathlib.Path(state.target_dir)
        if target.exists():
            for f in target.rglob("*.log"):
                state.logs.append(f.read_text(errors="replace"))
            for f in target.rglob("*.py"):
                state.code_snippets[str(f)] = f.read_text(errors="replace")
            log.debug(
                "Context collected | logs=%d | snippets=%d",
                len(state.logs),
                len(state.code_snippets),
            )
        else:
            log.warning(
                "Target directory '%s' not found — using stub data", state.target_dir
            )
            state.logs = ["[ERROR] NullPointerException at line 42 in app.py"]
            state.code_snippets = {
                "app.py": (
                    "def run():\n"
                    "    result = None\n"
                    "    return result.value  # Bug: None has no .value\n"
                )
            }
        return state

    def _assemble_result(self, state: DebuggerState) -> DebuggerState:
        if state.approved:
            state.final_result = (
                f"Fix APPROVED by {self._judge.role}.\n"
                f"Analysis: {state.analysis_output}\n"
                f"Fix applied: {state.proposed_fix}"
            )
        else:
            state.final_result = (
                f"Fix REJECTED by {self._judge.role}.\n"
                f"Judgment: {state.judgment}\n"
                "No changes applied."
            )
        return state
