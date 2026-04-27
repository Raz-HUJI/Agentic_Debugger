from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from config import AppConfig
from Debugger import ModularDebuggerFlow
from Debugger.ModularDebuggerFlow import BaseAgent, DebuggerState
from agents import BugFixerAgent, CodeQualityJudge
from utils import RubricLoader
from utils.result_writer import write_result

log = logging.getLogger("agent_fix")


# ---------------------------------------------------------------------------
# Triage-only pass-through judge — no rubric, no verdict, just analysis
# ---------------------------------------------------------------------------

class _PassThroughJudge(BaseAgent):
    @property
    def role(self) -> str:
        return "pass-through-judge"

    def run(self, state: DebuggerState) -> DebuggerState:
        state.approved = True
        state.judgment = "Triage mode — judgment skipped."
        return state


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def run_triage(args: argparse.Namespace, config: AppConfig) -> None:
    """Analyse a target directory for bugs without applying or judging a fix."""
    log.info("Starting triage | target='%s'", args.target_dir)

    flow = ModularDebuggerFlow(
        fixer_agent=BugFixerAgent(model=config.model_name),
        judge_agent=_PassThroughJudge(),
    )
    result = flow.kickoff(inputs={"target_dir": args.target_dir})
    log.info("Triage complete")

    if args.output:
        write_result(
            path=args.output,
            command="triage",
            target_dir=args.target_dir,
            state=flow.last_state,
        )

    print(result)


def run_fix(args: argparse.Namespace, config: AppConfig) -> None:
    """Run the full researcher → judge pipeline and optionally write result.json."""
    rubric_path: str = args.rubric
    log.info(
        "Starting %s | target='%s' | rubric='%s'",
        args.command,
        args.target_dir,
        rubric_path,
    )

    rubric = RubricLoader(rubric_path).load()
    log.info(
        "Rubric loaded | name='%s' | version=%s | criteria=%d | threshold=%.0f%%",
        rubric.name,
        rubric.version,
        len(rubric.criteria),
        rubric.pass_threshold * 100,
    )

    flow = ModularDebuggerFlow(
        fixer_agent=BugFixerAgent(model=config.model_name),
        judge_agent=CodeQualityJudge(rubric=rubric, model=config.model_name),
    )
    result = flow.kickoff(inputs={"target_dir": args.target_dir})

    verdict = "APPROVED" if flow.last_state.approved else "REJECTED"
    log.info("Pipeline complete | verdict=%s", verdict)

    if args.output:
        write_result(
            path=args.output,
            command=args.command,
            target_dir=args.target_dir,
            state=flow.last_state,
            rubric_name=rubric.name,
        )

    print(result)

    if not flow.last_state.approved:
        sys.exit(10)
