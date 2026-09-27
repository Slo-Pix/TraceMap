"""CLI entry point.

Usage::

    tracemap fix <trace-file>     # parse a crash file
    tracemap fix -                # read traceback from stdin
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text

from tracemap.engine import FixResult, run_fix
from tracemap.evidence import build_evidence
from tracemap.render import render_pack
from tracemap.theme import (
    ACCENT,
    GLYPH_DONE,
    GLYPH_FAILED,
    GLYPH_PENDING,
    GLYPH_RUNNING,
    MUTED,
    PASS,
    TEXT,
    TITLE,
    WARN,
)
from tracemap.verify import run_verify

console = Console(highlight=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _glyph(glyph_pair: tuple[str, str], label: str) -> Text:
    glyph, colour = glyph_pair
    t = Text()
    t.append(f" {glyph} ", style=f"bold {colour}")
    t.append(label, style=TEXT)
    return t


def _stage(label: str) -> None:
    console.print(_glyph(GLYPH_RUNNING, label))


def _done(label: str) -> None:
    console.print(_glyph(GLYPH_DONE, label))


def _pending(label: str) -> None:
    console.print(_glyph(GLYPH_PENDING, label))


def _failed(label: str) -> None:
    console.print(_glyph(GLYPH_FAILED, label))


def _print_fix_result(result: FixResult) -> None:
    """Render the FixResult to the terminal."""
    if result.pending:
        console.print()
        t = Text()
        t.append("bob", style=f"bold {ACCENT}")
        t.append(
            " is not on PATH — evidence pack written, fix is pending.",
            style=WARN,
        )
        console.print(t)
        console.print(Text(f"  Pack : {result.pack_path}", style=MUTED))
        console.print(
            Text(
                "  Paste the instruction from the .instruction.txt file into Bob when ready.",
                style=MUTED,
            )
        )
        return

    console.print()
    if result.rationale:
        t = Text()
        t.append("ROOT CAUSE  ", style=f"bold {TITLE}")
        t.append(result.rationale, style=TEXT)
        console.print(t)

    if result.patch_diff:
        console.print()
        console.print(Text("PATCH", style=f"bold {TITLE}"))
        console.print(Text(result.patch_diff, style=PASS))

    if result.test_path:
        console.print()
        t = Text()
        t.append("REGRESSION  ", style=f"bold {TITLE}")
        t.append(result.test_path, style=PASS)
        console.print(t)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """TraceMap — crash to green.

    Run with no arguments to open the Textual TUI.
    """
    if ctx.invoked_subcommand is None:
        from tracemap.tui import main as tui_main

        tui_main()


@main.command("tui")
@click.argument(
    "crash_file",
    metavar="[crash-file]",
    required=False,
    type=click.Path(exists=False, path_type=Path),
)
def tui_cmd(crash_file: Path | None) -> None:
    """Open the Textual TUI, optionally pre-loading a crash file."""
    from tracemap.tui import main as tui_main

    tui_main(crash_path=crash_file)


@main.command("fix")
@click.argument("trace_file", metavar="<trace-file|->")
@click.option(
    "--repo",
    "repo_path",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Root of the project to index. Defaults to the directory of the trace file.",
)
def fix_cmd(trace_file: str, repo_path: Path | None) -> None:
    """Parse a traceback and run the fix engine.

    Pass '-' to read the traceback from stdin.
    """
    # ── 1. Read traceback ──────────────────────────────────────────────────
    _stage("Reading traceback …")
    if trace_file == "-":
        trace_text = sys.stdin.read()
        trace_path: Path | None = None
    else:
        trace_path = Path(trace_file).resolve()
        if not trace_path.exists():
            _failed(f"File not found: {trace_file}")
            sys.exit(1)
        trace_text = trace_path.read_text(encoding="utf-8")

    # ── 2. Determine repo root ─────────────────────────────────────────────
    if repo_path is None:
        if trace_path is not None:
            repo_path = trace_path.parent
            # Walk up to a directory that looks like a repo root (has pyproject.toml / setup.py)
            for candidate in [trace_path.parent, *trace_path.parents]:
                if (candidate / "pyproject.toml").exists() or (candidate / "setup.py").exists():
                    repo_path = candidate
                    break
        else:
            repo_path = Path.cwd()
    _done(f"Repo root: {repo_path}")

    # ── 3. Build evidence ──────────────────────────────────────────────────
    _stage("Indexing repo and mapping frames …")
    try:
        pack = build_evidence(trace_text, repo_path)
    except Exception as exc:  # noqa: BLE001
        _failed(f"Evidence build failed: {exc}")
        sys.exit(1)
    _done(
        f"Evidence built — failing symbol: "
        f"{pack.failing_symbol.qualified_name if pack.failing_symbol else '(not in index)'}"
    )

    # ── 4. Render evidence pack ────────────────────────────────────────────
    render_pack(pack, console=console)

    # ── 5. Invoke Bob ──────────────────────────────────────────────────────
    _stage("Invoking Bob (tracemap-fixer) …")
    result = run_fix(pack, repo_path)

    if result.pending:
        _pending("Bob not available — fix is pending.")
    else:
        _done("Bob returned a response.")

    # ── 6. Print fix result ────────────────────────────────────────────────
    _print_fix_result(result)

    # ── 7. Verify (only when Bob actually ran and returned a diff) ─────────
    if not result.pending and result.patch_diff:
        _stage("Verifying — running covering tests …")
        test_paths = [sym.path for sym in pack.covering_tests]
        if test_paths:
            verify = run_verify(repo_path, test_paths)
            if verify.ok:
                _done(
                    f"All tests green after patch  "
                    f"({len(verify.passed_after)} passed, "
                    f"{len(verify.failed_after)} failed)"
                )
            else:
                _failed(f"Regressions introduced: {', '.join(verify.regression_introduced)}")
                sys.exit(2)
        else:
            _pending("No covering tests found — skipping verify step.")
    elif result.pending:
        _pending("Verification skipped (fix is pending).")
