#!/usr/bin/env python3
"""agent_fix — agentic code debugger CLI.

Usage:
    python agent_fix.py triage --target-dir ./app
    python agent_fix.py fix    --target-dir ./app [--rubric rubrics/security_rubric.json] [--output result.json]
    python agent_fix.py audit  --target-dir ./app --rubric rubrics/security_rubric.json  [--output result.json]

Exit codes:
    0   Success (triage complete, or fix approved)
    1   Configuration error (missing env vars)
    2   Input error (bad path, malformed rubric)
    3   Unexpected runtime error
    10  Fix pipeline ran but the judge rejected the proposed fix
"""
from __future__ import annotations

import argparse
import logging
import sys

from config import ConfigError, load_config
from cli.commands import run_fix, run_triage


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stderr,  # keep stdout clean for piping / result capture
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_fix",
        description="Agentic code debugger — triage, fix, and audit your codebase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Logging verbosity: DEBUG | INFO | WARNING | ERROR  (default: INFO)",
    )

    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # -- triage ---------------------------------------------------------------
    triage_p = sub.add_parser(
        "triage",
        help="Analyse a directory for bugs (no fix or judgment applied)",
    )
    triage_p.add_argument(
        "--target-dir", required=True, metavar="DIR",
        help="Path to the directory to analyse",
    )
    triage_p.add_argument(
        "--output", metavar="FILE",
        help="Write structured results to FILE as JSON",
    )

    # -- fix ------------------------------------------------------------------
    fix_p = sub.add_parser(
        "fix",
        help="Run the full pipeline: analyse -> propose fix -> judge",
    )
    fix_p.add_argument(
        "--target-dir", required=True, metavar="DIR",
        help="Path to the directory to debug",
    )
    fix_p.add_argument(
        "--rubric",
        default="rubrics/code_quality_rubric.json",
        metavar="FILE",
        help="Path to rubric JSON  (default: rubrics/code_quality_rubric.json)",
    )
    fix_p.add_argument(
        "--output", metavar="FILE",
        help="Write structured results to FILE as JSON",
    )

    # -- audit ----------------------------------------------------------------
    audit_p = sub.add_parser(
        "audit",
        help="Like 'fix' but the rubric argument is required",
    )
    audit_p.add_argument(
        "--target-dir", required=True, metavar="DIR",
        help="Path to the directory to audit",
    )
    audit_p.add_argument(
        "--rubric", required=True, metavar="FILE",
        help="Path to rubric JSON (required)",
    )
    audit_p.add_argument(
        "--output", metavar="FILE",
        help="Write structured results to FILE as JSON",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args.log_level)
    log = logging.getLogger("agent_fix")

    # --- config validation (fail fast, before any I/O) ---
    try:
        config = load_config()
    except ConfigError as exc:
        log.error("Configuration error: %s", exc)
        sys.exit(1)

    # --- dispatch ---
    try:
        if args.command == "triage":
            run_triage(args, config)
        elif args.command in ("fix", "audit"):
            run_fix(args, config)

    except FileNotFoundError as exc:
        log.error("File not found: %s", exc)
        sys.exit(2)
    except ValueError as exc:
        log.error("Invalid input: %s", exc)
        sys.exit(2)
    except SystemExit:
        raise  # let exit-code 10 (rejected fix) propagate cleanly
    except Exception as exc:
        log.error("Unexpected error: %s", exc)
        log.debug("Full traceback:", exc_info=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
