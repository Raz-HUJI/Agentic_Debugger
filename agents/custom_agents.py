from __future__ import annotations

import logging

from Debugger.ModularDebuggerFlow import BaseAgent, DebuggerState
from utils.rubric_loader import (
    CriterionScore,
    JudgmentOutput,
    Rubric,
    RubricCriterion,
)

log = logging.getLogger("agent_fix.agents")


class BugFixerAgent(BaseAgent):
    """Researcher role — scans code and logs to identify bugs and propose a fix."""

    def __init__(self, model: str = "stub") -> None:
        self._model = model

    @property
    def role(self) -> str:
        return "bug-fixer-researcher"

    def run(self, state: DebuggerState) -> DebuggerState:
        bugs_found: list[str] = []

        for filename, code in state.code_snippets.items():
            if "None" in code and ".value" in code:
                bugs_found.append(f"Potential NoneType dereference in {filename}")

        for entry in state.logs:
            if "ERROR" in entry or "Exception" in entry:
                bugs_found.append(f"Log error detected: {entry[:80]}")

        if bugs_found:
            log.info("Bugs found | count=%d", len(bugs_found))
            state.analysis_output = "Bugs found:\n" + "\n".join(bugs_found)
            state.proposed_fix = (
                "Add None-check before accessing .value attribute:\n"
                "  if result is not None:\n"
                "      return result.value\n"
                "  return default_value"
            )
        else:
            log.info("No bugs detected")
            state.analysis_output = "No obvious bugs detected."
            state.proposed_fix = "No fix required."

        return state


class CodeQualityJudge(BaseAgent):
    """Configurable Judge — evaluates the proposed fix against an injected rubric.

    The rubric is loaded externally (via RubricLoader) and injected here,
    making the judge fully agnostic of any specific rubric file. Swapping
    rubrics requires no changes to this class.
    """

    def __init__(self, rubric: Rubric, model: str = "stub") -> None:
        self._rubric = rubric
        self._model = model

    @property
    def role(self) -> str:
        return f"code-quality-judge [{self._rubric.name}]"

    # ------------------------------------------------------------------
    # Public interface (BaseAgent)
    # ------------------------------------------------------------------

    def run(self, state: DebuggerState) -> DebuggerState:
        prompt = self._build_prompt(state)
        log.debug(
            "Prompt built | chars=%d | criteria=%d",
            len(prompt),
            len(self._rubric.criteria),
        )

        # Production path: send `prompt` to LLM, parse raw JSON response, then
        # call self._validate_output(raw_dict) to enforce the schema.
        # Stub path: run deterministic heuristics and validate through the same
        # schema so the contract is identical regardless of backend.
        raw_judgment = self._evaluate(state)
        validated: JudgmentOutput = self._validate_output(raw_judgment.model_dump())

        state.judgment_output = validated
        state.judgment = validated.model_dump_json(indent=2)
        state.approved = validated.approved
        log.info(
            "Judgment complete | score=%.0f%% | approved=%s",
            validated.overall_score * 100,
            validated.approved,
        )
        return state

    # ------------------------------------------------------------------
    # Prompt construction — driven entirely by rubric data
    # ------------------------------------------------------------------

    def _build_prompt(self, state: DebuggerState) -> str:
        """Dynamically construct the LLM prompt from the loaded rubric criteria.

        Changing the rubric file produces a completely different prompt with
        no code changes required.
        """
        criteria_block = "\n".join(
            f"  {i + 1}. {c.name} (id={c.id}, weight={c.weight:.0%})\n"
            f"     {c.description}"
            for i, c in enumerate(self._rubric.criteria)
        )
        return (
            f"You are a code quality judge. Evaluate the proposed fix strictly "
            f"using the rubric below. Return ONLY a JSON object — no prose.\n\n"
            f"RUBRIC: {self._rubric.name} (v{self._rubric.version})\n"
            f"Description: {self._rubric.description}\n"
            f"Pass threshold: {self._rubric.pass_threshold:.0%}\n\n"
            f"CRITERIA:\n{criteria_block}\n\n"
            f"PROPOSED FIX:\n{state.proposed_fix}\n\n"
            f"ANALYSIS CONTEXT:\n{state.analysis_output}\n\n"
            "Required JSON schema:\n"
            "{\n"
            '  "approved": bool,\n'
            '  "overall_score": float (0.0–1.0),\n'
            '  "rubric_name": str,\n'
            '  "criterion_scores": [\n'
            '    {"id": str, "name": str, "score": float (0.0–1.0), "rationale": str}\n'
            "  ],\n"
            '  "summary": str\n'
            "}"
        )

    # ------------------------------------------------------------------
    # Structured response validator
    # ------------------------------------------------------------------

    def _validate_output(self, raw: dict) -> JudgmentOutput:
        """Validate that raw judge output conforms to JudgmentOutput schema.

        In production this is called on the LLM's parsed JSON response.
        Raises pydantic.ValidationError if the structure is invalid.
        """
        return JudgmentOutput.model_validate(raw)

    # ------------------------------------------------------------------
    # Stub evaluation — replace body with LLM call for production
    # ------------------------------------------------------------------

    def _evaluate(self, state: DebuggerState) -> JudgmentOutput:
        """Score each rubric criterion with keyword heuristics (stub only)."""
        fix = state.proposed_fix.lower()
        analysis = state.analysis_output.lower()

        def _score(criterion: RubricCriterion) -> CriterionScore:
            cid = criterion.id.lower()
            cname = criterion.name.lower()

            if any(k in cid or k in cname for k in ("null", "none", "safety", "guard")):
                hit = "is not none" in fix or "none check" in fix
                score = 0.9 if hit else 0.2
                rationale = "Fix includes None guard." if hit else "Fix lacks None guard."

            elif any(k in cid or k in cname for k in ("read", "style", "idiom", "clean", "format")):
                hit = len(fix) > 20 and "\n" in fix
                score = 0.8 if hit else 0.5
                rationale = "Fix is multi-line and readable." if hit else "Fix is terse."

            elif any(k in cid or k in cname for k in ("complet", "cover", "address", "all")):
                hit = "bugs found" in analysis
                score = 0.85 if hit else 0.5
                rationale = "Fix addresses identified bugs." if hit else "Coverage unclear."

            elif any(k in cid or k in cname for k in ("secur", "inject", "sanitiz", "escape")):
                score = 0.3
                rationale = "Stub: security analysis requires full LLM review."

            elif any(k in cid or k in cname for k in ("perform", "complex", "effici", "optim")):
                score = 0.5
                rationale = "Stub: performance impact indeterminate without profiling."

            else:
                score = 0.5
                rationale = f"Stub: no heuristic for criterion '{criterion.name}'."

            return CriterionScore(
                id=criterion.id,
                name=criterion.name,
                score=score,
                rationale=rationale,
            )

        scores = [_score(c) for c in self._rubric.criteria]
        overall = round(
            sum(s.score * c.weight for s, c in zip(scores, self._rubric.criteria)), 3
        )
        approved = overall >= self._rubric.pass_threshold

        return JudgmentOutput(
            approved=approved,
            overall_score=overall,
            rubric_name=self._rubric.name,
            criterion_scores=scores,
            summary=(
                f"Overall score {overall:.0%} "
                f"{'meets' if approved else 'is below'} the "
                f"{self._rubric.pass_threshold:.0%} pass threshold."
            ),
        )
