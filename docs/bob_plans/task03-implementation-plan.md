# TraceMap — Implementation Plan

## Governing Rules and Guidelines

This plan is governed by the constraints in [`tracemap/AGENTS.md`](AGENTS.md) and the project
overview in [`plan.md`](../plan.md). Every decision below traces directly to those documents.

| Rule | Source |
|---|---|
| CodeMap is read-only — never edit `codemap-ref/` | AGENTS.md §DEPENDENCY POLICY |
| Never shell out to `codemap trace/impact/refs` — no `--json` | AGENTS.md §5 |
| Colours ONLY from `tracemap/tracemap/theme.py` — never a hex literal | AGENTS.md §CONVENTIONS |
| Fully typed, `from __future__ import annotations`, Python ≥ 3.11 | AGENTS.md §CONVENTIONS |
| `ruff` + `ruff format`; no line > 100 chars | AGENTS.md §CONVENTIONS |
| Every fix ships a regression test; verify FAIL-before / PASS-after | AGENTS.md §HARD RULES |
| Blast-radius tests must stay green after the fix | AGENTS.md §HARD RULES |
| No speculative features — implement only what is in the current milestone | AGENTS.md §HARD RULES |
| pytest is the only test runner wired | AGENTS.md §SCOPE |

---

## Top-Level Overview

TraceMap bridges a raw Python crash to a verified, battle-tested fix in five sequential stages:

1. **Evidence** (`evidence.py`) — parse the traceback and query CodeMap to build a structured
   `EvidencePack` (failing frame, source, callers, callees, blast radius, covering tests).
2. **Engine** (`engine.py`) — pass the evidence pack to IBM Bob via the `tracemap-fixer` Skill
   and capture a `FixResult` (patch diff, test path, rationale).
3. **Verify** (`verify.py`) — run the new regression test before and after applying the patch
   to prove FAIL-before / PASS-after.
4. **CLI** (`cli.py`) — wire the three stages into `tracemap fix <trace-file|->`.
5. **TUI** (`tui.py`) — a Textual app that drives the same pipeline with a live pipeline rail
   and a frame inspector, matching CodeMap's visual grammar.

**What is already built (do not recreate):** `theme.py`, `__init__.py`, `examples/buggy_app/`,
`LICENSE`, `NOTICE`, `pyproject.toml`.

**Demo fixture:** `examples/buggy_app/crash.txt` — a real `ZeroDivisionError` from
`divide_total()` in `report.py` triggered because `training` category has zero entries.

---

## Sub-Task 1 — `evidence.py`: Traceback → EvidencePack

**Status:** `[ ] pending`

### Intent
Build the data-gathering layer. Consume the CodeMap Python API to convert raw traceback text
into a structured, self-contained evidence pack that Bob (and the TUI) can consume without
further file access.

### Public API

```python
# tracemap/tracemap/evidence.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from codemap.model import Symbol
from codemap.trace import Frame

@dataclass(frozen=True)
class EvidencePack:
    failing_frame: Frame                    # innermost crash frame (index 0 of parse_trace)
    failing_symbol: Symbol | None           # None when not in the index
    source: str                             # full source of the failing symbol's file
    callers: list[str]                      # direct caller symbol IDs (incoming calls)
    callees: list[str]                      # direct callee symbol IDs (outgoing calls)
    blast_radius: list[tuple[str, int]]     # [(symbol_id, depth), ...] BFS order
    covering_tests: list[Symbol]            # test functions that transitively call failing_symbol
    unmapped_frames: list[Frame]            # frames where map_frames returned None

def build_evidence(trace_text: str, repo: Path) -> EvidencePack: ...
def render_markdown(pack: EvidencePack) -> str: ...
```

**`build_evidence` steps (in order):**
1. `load_or_build(repo)` → `CodeIndex` (preferred over `build_index`; returns cache hit flag).
2. `parse_trace(trace_text)` → `list[Frame]` (index 0 = crash site).
3. `map_frames(index, frames)` → `list[tuple[Frame, Symbol | None]]`.
4. Identify the crash frame: first frame where `Symbol is not None`; if all are `None`, use
   `frames[0]` and set `failing_symbol = None`.
5. Build `callers` from `index.incoming(failing_symbol.id)` → extract `.caller_id` (filter `None`).
6. Build `callees` from `index.outgoing(failing_symbol.id)` → extract `.resolved_ids` (flatten).
7. Build `blast_radius` from `index.transitive_callers(failing_symbol.id, max_depth=20)`.
8. Build `covering_tests` using the `tests_covering` helper pattern from AGENTS.md §4 (filter
   `transitive_callers` to `is_test_path` + name starts with `test`).
9. Collect `unmapped_frames` from pairs where `Symbol is None`.
10. Return frozen `EvidencePack`.

**`render_markdown` produces:** failing frame block, failing symbol source (fenced), callers list,
callees list, blast-radius table (symbol id + depth), covering tests list.
Compact enough to fit in a Bob context window.

**CodeMap API uncertainty flags:**
- `incoming` Call objects have `.caller_id: str | None` — plan filters `None`.
- `outgoing` Call objects have `.resolved_ids: tuple[str, ...]` — may be empty tuple when
  unresolved; plan flattens and deduplicates.
- `failing_symbol` may be `None` for frozen `runpy` frames; plan handles gracefully.

### Expected Outcomes
- `EvidencePack` is importable; all fields typed correctly.
- `build_evidence(crash_txt, buggy_app_root)` returns a pack where `failing_symbol.name == "divide_total"`.
- `pack.blast_radius` is non-empty.
- `render_markdown(pack)` returns a non-empty string containing the word `divide_total`.

### Todo List
1. Create `tracemap/tracemap/evidence.py` with the `EvidencePack` dataclass and both public functions.
2. Create `tracemap/tests/__init__.py` (empty) so pytest collects the tests directory.
3. Create `tracemap/tests/test_evidence.py` asserting the above outcomes against `crash.txt`.

### Relevant Context
- CodeMap API: [`tracemap/AGENTS.md`](AGENTS.md) §2–4
- Fixture: [`tracemap/examples/buggy_app/crash.txt`](examples/buggy_app/crash.txt)
- Bug: `divide_total` in [`tracemap/examples/buggy_app/report.py`](examples/buggy_app/report.py) line 10
- `is_test_path` import: `from codemap.model import is_test_path`

---

## Sub-Task 2 — `render.py`: Terminal Evidence Rendering

**Status:** `[ ] pending`

### Intent
Separate rendering concerns from data concerns. Produce a Rich-based terminal renderer for
`EvidencePack` that imports every colour from `theme.py` and never writes a hex literal.

### Public API

```python
# tracemap/tracemap/render.py
from __future__ import annotations
from rich.console import Console
from .evidence import EvidencePack

def print_evidence(pack: EvidencePack, console: Console | None = None) -> None: ...
def format_frame_table(pack: EvidencePack) -> rich.table.Table: ...
```

**`print_evidence`:** prints the crash frame (FAIL colour), callers (INFO colour), callees (INFO),
blast-radius count (WARN), covering tests (PASS). Uses `Rich` `Panel` with `BORDER` colour and
`TITLE` for headings. `Console` defaults to `Console()` when `None`.

**`format_frame_table`:** returns a `rich.table.Table` with columns `#`, `symbol`, `file:line`,
`role` (`crash frame` / `caller` / other), `indexed`. Unindexed rows styled `MUTED`.
Crash-site row styled `FAIL`. No hex literals anywhere.

### Expected Outcomes
- `print_evidence` produces output without raising.
- No hex literal exists anywhere in `render.py`.
- Every colour import resolves to a constant from `theme.py`.

### Todo List
1. Create `tracemap/tracemap/render.py` with both functions.
2. Add a smoke test in `tracemap/tests/test_render.py` that calls `print_evidence` with a
   `Console(file=io.StringIO())` and asserts the output contains `divide_total`.

### Relevant Context
- Palette: [`tracemap/tracemap/theme.py`](tracemap/theme.py)
- `EvidencePack`: Sub-Task 1 above

---

## Sub-Task 3 — `engine.py`: Evidence Pack → FixResult via IBM Bob

**Status:** `[ ] pending`

### Intent
Drive IBM Bob non-interactively with the `tracemap-fixer` Skill. Capture its output as a
`FixResult`. If Bob cannot be invoked headlessly, write the evidence pack to `.tracemap/pack.md`
and return a `pending` result — never fake or stub a fix.

### Public API

```python
# tracemap/tracemap/engine.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .evidence import EvidencePack

@dataclass(frozen=True)
class FixResult:
    patch_diff: str          # unified diff of the proposed fix (empty string when pending)
    test_path: str           # path to the generated regression test (empty string when pending)
    rationale: str           # Bob's short explanation
    raw_response: str        # full Bob response text
    pending: bool            # True when Bob was not invokable headlessly

def run_fix(pack: EvidencePack, repo: Path) -> FixResult: ...
```

**`run_fix` strategy:**
1. Call `render_markdown(pack)` to produce the context string.
2. Attempt to invoke the `tracemap-fixer` Skill non-interactively (mechanism TBD; determined
   during implementation — do not stub or guess an invocation path here).
3. If invocation succeeds: parse Bob's response for the patch diff and test path; return
   `FixResult(pending=False, ...)`.
4. If invocation is not available: write `render_markdown(pack)` + a ready-to-paste prompt
   to `.tracemap/pack.md`; return `FixResult(pending=True, patch_diff="", test_path="", ...)`.

**Open question (flagged):** The headless Bob invocation mechanism is not defined in AGENTS.md.
During implementation, consult the Bob API or SDK documentation. Do NOT invent or hardcode an
invocation path before it is confirmed.

### Expected Outcomes
- `FixResult` is importable and frozen.
- `run_fix` either returns a real `FixResult` with a non-empty `patch_diff`, or returns
  `FixResult(pending=True)` with `.tracemap/pack.md` written — never silently returns empty data.

### Todo List
1. Create `tracemap/tracemap/engine.py` with `FixResult` and `run_fix`.
2. Add `tracemap/tests/test_engine.py` with a test that mocks the Bob call and asserts
   both the success and the `pending=True` fallback paths.

### Relevant Context
- Evidence layer: Sub-Task 1
- `tracemap-fixer` Skill: authored in task05 (before this module is implemented in task06)
- AGENTS.md §HARD RULES rule 3 (headless fallback, never fake)

---

## Sub-Task 4 — `cli.py`: `tracemap fix <trace-file|->`

**Status:** `[ ] pending`

### Intent
Wire `evidence → engine → verify` into a single CLI command. Produce readable terminal output
using `render.py`. Be honest about what actually ran.

### Public API

```python
# tracemap/tracemap/cli.py
from __future__ import annotations

def main() -> None: ...          # entrypoint registered in pyproject.toml
```

**`main` behaviour:**
- Subcommand: `tracemap fix <trace-file|->` (use `argparse` or `sys.argv` — no external CLI lib).
- Read traceback text from the specified file path, or from stdin when the argument is `-`.
- Infer `repo` as the current working directory unless `--repo <path>` is supplied.
- Call `build_evidence` → `run_fix` → `verify` in sequence.
- After each stage print a status line using `GLYPH_*` constants from `theme.py`.
- On `FixResult(pending=True)`: print the path to `.tracemap/pack.md` and exit 0 (not an error).
- On verify pass: print the proof summary (PASS in green); exit 0.
- On verify fail: print FAIL output; exit 1.
- Errors (file not found, CodeMap index failure): print to stderr; exit 2.

### Expected Outcomes
- `tracemap fix tracemap/examples/buggy_app/crash.txt` runs end to end without raising.
- Output contains at least one stage status glyph.
- Exit code is 0 on success or pending, 1 on verify failure, 2 on error.

### Todo List
1. Create `tracemap/tracemap/cli.py` with `main()`.
2. Add `tracemap/tests/test_cli.py` that monkey-patches `build_evidence`, `run_fix`, and
   `verify` and asserts exit codes for each path.

### Relevant Context
- Entry point already declared: `tracemap/pyproject.toml` → `tracemap = "tracemap.cli:main"`
- Stage glyphs: `GLYPH_PENDING`, `GLYPH_RUNNING`, `GLYPH_DONE`, `GLYPH_FAILED` from `theme.py`

---

## Sub-Task 5 — `verify.py`: Fail-Before / Pass-After Runner

**Status:** `[ ] pending`

### Intent
Prove the fix claim. Run the regression test against the original code, then re-run it after
applying the patch. Emit a `VerifyResult` that is honest: if it did not fail before, say so
rather than fabricating a green proof.

### Public API

```python
# tracemap/tracemap/verify.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class VerifyResult:
    failed_before: bool
    passed_after: bool
    output_before: str      # raw pytest output (pre-patch)
    output_after: str       # raw pytest output (post-patch)

def verify(repo: Path, test_path: str, patch_diff: str) -> VerifyResult: ...
```

**`verify` steps:**
1. Write `patch_diff` to a temporary `.patch` file.
2. Run `pytest <test_path> -q` (no patch applied) via `subprocess.run`; capture stdout+stderr;
   set `failed_before = returncode != 0`.
3. Apply the patch with `patch -p1` inside `repo`.
4. Run `pytest <test_path> -q` again; capture stdout+stderr; set `passed_after = returncode == 0`.
5. Reverse-apply the patch (restore original state) so the repo is clean after verification.
6. Return `VerifyResult`.

**Guard:** if `patch_diff` is empty (pending fix), return
`VerifyResult(failed_before=False, passed_after=False, output_before="", output_after="")` immediately.

### Expected Outcomes
- `verify(buggy_app_root, test_path, valid_patch)` returns `VerifyResult(failed_before=True, passed_after=True)`.
- Repo files are unchanged after `verify` completes (patch is reversed).
- `VerifyResult` is importable and frozen.

### Todo List
1. Create `tracemap/tracemap/verify.py` with `VerifyResult` and `verify`.
2. Add `tracemap/tests/test_verify.py` using a trivial synthetic patch and an always-failing
   test to assert both the `failed_before` and `passed_after` fields.

### Relevant Context
- pytest is the only runner: AGENTS.md §SCOPE
- `patch -p1` is a standard POSIX utility; assume it is available in the target environment
- Hard rule: never claim a fix is verified when it was not actually run (AGENTS.md §HARD RULES)

---

## Sub-Task 6 — `tui.py`: Textual TUI

**Status:** `[ ] pending`

### Intent
A Textual application (`tracemap` with no arguments) that drives the full pipeline with a live
pipeline rail. Must mirror CodeMap's visual grammar exactly — same round borders, `:focus-within`
ACCENT recolouring, 1-cell scrollbars — but use the amber TraceMap theme, not CodeMap's green.

### Public API

```python
# tracemap/tracemap/tui.py
from __future__ import annotations
from textual.app import App

class TraceMapApp(App): ...

def run() -> None: ...          # called from cli.py when no subcommand is given
```

**Layout (from AGENTS.md §LAYOUT and plan.md §TRACEMAP TUI LAYOUT SPEC):**

| Pane | Position | Details |
|---|---|---|
| PIPELINE rail | Left, width 36 | 5 stages with live `GLYPH_*` glyphs; updates during `run_fix` |
| TRACEBACK | Main top, height 3 | Paste or load a traceback |
| FRAMES | Main 1fr | `DataTable`: `#`, symbol, `file:line`, role, indexed. Crash frame = FAIL. Unmapped = MUTED |
| INSPECTOR | height 18, toggled by `x` | Source preview, callers/callees `OptionList`, blast-radius count, covering tests |
| PROOF modal | Toggled by `p` | Patch diff, before block (FAIL), after block (PASS) |

**Key bindings:** `t` paste trace · `x` expand inspector · `b` blast radius · `enter`/`v` open in
editor · `f` run the Bob fix · `p` proof · `?` help · `ctrl+d` quit.

**CSS rule:** build the entire CSS string as an f-string over `theme.py` constants.
No hex literal anywhere in `tui.py`.

**Acceptance:** `tracemap` (no args) launches, loads `examples/buggy_app/crash.txt`, shows
correctly mapped frames, and `f` drives the REAL engine with the pipeline rail updating live.

### Expected Outcomes
- `run()` starts the Textual app without raising.
- PIPELINE rail transitions through all five glyphs during a fix run.
- All colours resolve to `theme.py` constants — no hex in `tui.py`.

### Todo List
1. Create `tracemap/tracemap/tui.py` with `TraceMapApp` and `run()`.
2. Study `codemap-ref/src/codemap/tui.py` for the border/focus-within/scrollbar patterns
   before writing a single line of CSS.
3. Wire `cli.py` `main()` to call `run()` when invoked with no arguments.
4. Add `tracemap/tests/test_tui.py` — a Textual pilot test that mounts the app, checks the
   pipeline rail is visible, and confirms the FRAMES table has at least one row after loading
   the `crash.txt` fixture.

### Relevant Context
- CodeMap TUI reference: `codemap-ref/src/codemap/tui.py` (read-only)
- Palette: [`tracemap/tracemap/theme.py`](tracemap/theme.py)
- Engine: Sub-Task 3 (`run_fix`)
- Evidence: Sub-Task 1 (`build_evidence`)
- If running short on time: ship pipeline rail + frames table + theme; cut inspector + proof modal

---

## Execution Order

```
Sub-Task 1 (evidence.py)
    ↓
Sub-Task 2 (render.py)    ← can be done in parallel with Sub-Task 1
    ↓
Sub-Task 3 (engine.py)    ← depends on EvidencePack from Sub-Task 1
    ↓
Sub-Task 5 (verify.py)    ← can be done in parallel with Sub-Task 3
    ↓
Sub-Task 4 (cli.py)       ← wires Sub-Tasks 1, 3, 5
    ↓
Sub-Task 6 (tui.py)       ← wires Sub-Tasks 1, 3, 4, 5
```

Note: Sub-Tasks 1+2 and Sub-Tasks 3+5 are natural candidates for parallel subagent dispatch
(as called for in task04 of the build plan).

---

## Open Questions / Flags

1. **Headless Bob invocation** (`engine.py`): The mechanism for calling IBM Bob non-interactively
   from Python is not specified in AGENTS.md. This must be confirmed before implementing
   `run_fix`. The fallback path (write `.tracemap/pack.md`) is the safety valve.
2. **`incoming` Call shape**: AGENTS.md shows `.caller_id: str | None` — confirm the field name
   is exactly `caller_id` when reading the CodeMap source before using it.
3. **`outgoing` resolved_ids**: May be an empty tuple for external/unresolved calls — deduplicate
   and skip empties.
4. **`patch` availability**: `verify.py` uses the POSIX `patch` utility. Confirm it is present
   in the target environment; if not, fall back to `python-patch` or `unidiff`.
