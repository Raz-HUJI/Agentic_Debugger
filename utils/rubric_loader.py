from __future__ import annotations

import json
import pathlib
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Rubric schema — validated on load
# ---------------------------------------------------------------------------

class RubricCriterion(BaseModel):
    id: str
    name: str
    description: str
    weight: float = Field(gt=0, le=1)


class Rubric(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    pass_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    criteria: list[RubricCriterion] = Field(min_length=1)

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> Rubric:
        total = sum(c.weight for c in self.criteria)
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Criterion weights must sum to 1.0, got {total:.2f}"
            )
        return self


# ---------------------------------------------------------------------------
# Structured response types — judge output is validated against these
# ---------------------------------------------------------------------------

class CriterionScore(BaseModel):
    id: str
    name: str
    score: float = Field(ge=0.0, le=1.0)
    rationale: str


class JudgmentOutput(BaseModel):
    approved: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    rubric_name: str
    criterion_scores: list[CriterionScore]
    summary: str


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class RubricLoader:
    """Reads, parses, and validates a rubric JSON file.

    Supports any rubric that follows the shared schema, so swapping
    security_rubric.json for performance_rubric.json requires only changing
    the path passed to the constructor.
    """

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)

    def load(self) -> Rubric:
        """Return a validated Rubric.

        Raises:
            FileNotFoundError: rubric file does not exist at the given path.
            ValueError: JSON is malformed or fails schema validation.
        """
        if not self._path.exists():
            raise FileNotFoundError(
                f"Rubric file not found: {self._path.resolve()}"
            )

        try:
            raw: dict[str, Any] = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in rubric file '{self._path}': {exc}"
            ) from exc

        try:
            return Rubric.model_validate(raw)
        except Exception as exc:
            raise ValueError(
                f"Rubric schema validation failed for '{self._path}': {exc}"
            ) from exc
