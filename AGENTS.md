# TraceMap — Agent Briefing

## GOAL

TraceMap = **crash → CodeMap evidence pack → Bob writes a verified fix + regression test
that FAILS BEFORE and PASSES AFTER.**

A developer pastes a failing Python traceback (or points at a failing pytest run). TraceMap:
1. Indexes the target repo via CodeMap's Python API.
2. Maps each traceback frame to an indexed symbol.
3. Builds a compact JSON/Markdown **evidence pack**: failing frame, function source, callers,
   callees, transitive blast radius, and candidate covering tests.
4. Feeds the evidence pack to IBM Bob 2.0 (Agent mode) with the instruction to write a fix
   **plus** a regression test that fails before and passes after.
5. Runs the affected test subset to prove fail-before / pass-after.
6. Emits: patch diff + new test + before/after evidence + short writeup.

---

## DEPENDENCY POLICY

**CodeMap (Apache-2.0) is a pre-existing, read-only dependency.**

- Source lives in `codemap-ref/` — gitignored, but READABLE by Bob (not bobignored). **Never edit it.**
- Consume it only via its Python API (see below).
- Ship a `NOTICE` file crediting CodeMap's Apache-2.0 licence.
- TraceMap itself is MIT.

---

## EXACT CODEMAP PYTHON API

### 1. Build / load an index

```python
from codemap.indexer import build_index          # always rebuild from source
from codemap.cache   import load_or_build        # cache-aware (preferred)
from codemap.model   import CodeIndex

# Preferred: returns (CodeIndex, cache_hit: bool)
index, from_cache = load_or_build("/path/to/repo")

# Or always-rebuild:
index: CodeIndex = build_index("/path/to/repo")
```

`CodeIndex` fields:
```
index.root              Path          # absolute root of the indexed tree
index.symbols           dict[str, Symbol]   # symbol_id → Symbol
index.calls             list[Call]
index.imports           list[ImportEdge]
index.files_scanned     int
index.errors            list[str]
```

---

### 2. Traceback → mapped symbols

**Step A – parse raw traceback text into frames (crash site first)**

```python
from codemap.trace import parse_trace, Frame

frames: list[Frame] = parse_trace(traceback_text)
# Frame.path  str   – file path as it appears in the traceback
# Frame.line  int   – line number
# Frame.name  str   – function name (or "<module>")
# ORDER: index 0 = crash site (innermost); last = outermost caller
```

Understands: classic Python `File "…", line N, in name`,
Rich `path:line in name`, and Node/V8 `at fn (path:l:c)`.

**Step B – map frames to CodeIndex symbols**

```python
from codemap.trace import map_frames
from codemap.model import Symbol

mapped: list[tuple[Frame, Symbol | None]] = map_frames(index, frames)
# Same order as `frames`: index 0 = crash site.
# Symbol is None when the frame is not inside an indexed callable.
```

`map_frames` resolves each frame by absolute path then falls back to path-suffix
matching, picks the smallest containing callable (function/method/class) by line span,
and falls back to name matching when no spanning symbol exists.

---

### 3. Callers, callees, and blast radius

```python
# Direct callees of a symbol (what it calls)
outgoing: list[Call] = index.outgoing(symbol.id)
# Each Call: .callee_name str, .resolved_ids tuple[str,...], .path, .line, .column

# Direct callers of a symbol (who calls it)
incoming: list[Call] = index.incoming(symbol.id)
# Each Call: .caller_id str | None

# Transitive callers – full blast radius (BFS, breadth-first, shallowest first)
blast: list[tuple[str, int]] = index.transitive_callers(
    symbol.id,
    max_depth=20,   # default
)
# Returns [(caller_id, depth), ...] in BFS order (depth 1 = direct callers first)
# Resolve to Symbol: index.symbols[caller_id]

# All call chains from source → target
paths: list[list[str]] = index.call_paths(
    source_id, target_id,
    max_depth=12,   # default
    limit=50,       # default
)
# Each inner list is a chain of symbol_ids, shortest chains first.
```

---

### 4. Find tests covering a symbol

CodeMap has no dedicated "tests for symbol X" query. Use `transitive_callers` and
filter to test symbols by path heuristic:

```python
from codemap.model import is_test_path

def tests_covering(index: CodeIndex, symbol_id: str) -> list[Symbol]:
    blast = index.transitive_callers(symbol_id)
    return [
        index.symbols[sid]
        for sid, _depth in blast
        if sid in index.symbols
        and index.symbols[sid].kind in {"function", "method"}
        and index.symbols[sid].name.lower().startswith("test")
        and is_test_path(index.symbols[sid].path)
    ]
```

`is_test_path(path)` returns True when any parent directory is named
`tests / test / __tests__ / spec / specs`, or the filename starts with `test` or
contains `_test.` / `.test.` / `.spec.`.

For git-diff-driven test selection (affected by a commit range) use
`codemap.affected.affected_tests(root, range_spec)` — returns a dict with
`"tests"`, `"files"`, and a ready `"command"` string for pytest.

---

### 5. Which CLI subcommands support `--json`?

| Subcommand  | `--json` flag |
|-------------|:-------------:|
| `scan`      | ✅ yes         |
| `check`     | ✅ yes         |
| `review`    | ✅ yes         |
| `affected`  | ✅ yes         |
| `find`      | ❌ no          |
| `refs`      | ❌ no          |
| `paths`     | ❌ no          |
| `impact`    | ❌ no          |
| `cycles`    | ❌ no          |
| `hotspots`  | ❌ no          |
| `roles`     | ❌ no          |
| `trace`     | ❌ no          |
| `graph`     | ❌ no          |
| `explore`   | ❌ no          |

**`codemap trace`, `codemap impact`, `codemap refs` have NO `--json` flag.**
TraceMap must use the Python API for these operations and must never shell out
to those subcommands expecting JSON output.

---

## SCOPE

- **Python-only end to end.** TraceMap indexes Python repos only.
- **pytest is the only test runner wired.**
- Target Python ≥ 3.11.
- Licence: MIT (new code); Apache-2.0 NOTICE for CodeMap.

---

## CONVENTIONS

| Convention | Rule |
|---|---|
| Language | Python 3.11+ |
| Test runner | pytest only |
| Typing | fully typed, `from __future__ import annotations` |
| Modules | small, single-responsibility |
| Colours | **only** from `tracemap/tracemap/theme.py` — import its real constants (see below). Never write a hex literal. |
| Style | `ruff` + `ruff format`; no line > 100 chars |
| Commits | one atomic commit per meaningful step; append COMMS LOG entry before each commit |

### `theme.py` palette contract

`tracemap/tracemap/theme.py` ALREADY EXISTS. These are its real constant names — import
them, do not invent new ones:

```python
BG PANEL HOVER BORDER          # surfaces: #0e0e0e #141414 #1f1f1f #3c3c3c
ACCENT ACCENT_DIM              # amber #e8a33d #a8762c  (CodeMap uses green #90ee90)
TEXT TITLE MUTED               # #d4d4d4 #e6e6e6 #7d7d7d
PASS FAIL WARN INFO            # #7fd08a #e06c6c #e6d690 #8fd0e6
GLYPH_PENDING GLYPH_RUNNING GLYPH_DONE GLYPH_FAILED   # (glyph, colour) pairs
```

ACCENT is amber, never green: GREEN/RED are reserved for test outcomes so the
fail-before/pass-after proof reads unambiguously.

Never introduce colour literals anywhere else; import from `theme`.

---

## HARD RULES

1. **Every fix ships a regression test** that is demonstrably RED before the fix and
   GREEN after. The verify step must prove both states.
2. **Never edit `codemap-ref/`**. It is read-only. Do not monkey-patch CodeMap internals.
3. **Never shell out to `codemap trace/impact/refs`** — they have no `--json`.
   Use the Python API.
4. **Blast-radius awareness**: the fix must not break any caller that was green before.
   Run the full blast-radius test set, not just the single failing test.
5. **No speculative features**: implement only what is in the current milestone.

---

## PROJECT LAYOUT

```
tracemap/               ← git root (MIT)
├── AGENTS.md           ← this file
├── LICENSE             ← MIT
├── NOTICE              ← Apache-2.0 credit for CodeMap
├── README.md
├── pyproject.toml
├── tracemap/           ← package
│   ├── __init__.py
│   ├── theme.py        ← colour constants (single source of truth)
│   ├── evidence.py     ← traceback → evidence pack (CodeMap API calls here)
│   ├── render.py       ← terminal rendering, colours from theme.py
│   ├── engine.py      ← Bob-driven fix loop (the module is engine.py, NOT fixer.py)
│   ├── verify.py       ← fail-before / pass-after runner
│   ├── cli.py          ← `tracemap fix <trace>` entrypoint
│   └── tui.py          ← Textual TUI (Phase 5)
├── tests/              ← TraceMap's own tests
│   └── test_evidence.py
├── examples/           ← sample buggy project (ALREADY BUILT — do not recreate)
│   └── buggy_app/
│       ├── loader.py   ← CATEGORIES + expense records
│       ├── report.py   ← contains the bug: divide_total() divides by zero
│       ├── main.py     ← entry point that crashes
│       ├── crash.txt   ← the REAL captured traceback (the demo's input)
│       └── tests/test_report.py  ← 3 tests that PASS despite the bug
├── docs/               ← architecture.md, proof.md
└── bob_sessions/       ← Bob session screenshots — MUST BE COMMITTED, never gitignored.
                          This is the hackathon's required evidence.
```

---

## BUILD PHASES (reference — see ../plan.md for the prompts)

| Task | Owner | Bob capability | Description |
|------|-------|----------------|-------------|
| task01 | A | understand codebase | ✅ DONE — this file |
| task02 | B | flowchart | docs/architecture.md, two Mermaid diagrams |
| task03 | A | implementation plan | Plan mode: full build plan |
| task04 | A | parallel agents | evidence.py + tests + render.py via 3 subagents |
| task05 | A | skills | author the "tracemap-fixer" Skill (the runtime engine) |
| task06 | A | build feature | engine.py + cli.py |
| task07 | B | — | verify.py + docs/proof.md |
| task08 | B | build feature | tui.py |
| task09 | B | review code | Bob review over the diff |
| task10 | B | — | README, docstrings, conventional commit |

ALREADY BUILT BY HAND (do not recreate): theme.py, examples/buggy_app/ incl. crash.txt,
LICENSE, NOTICE, pyproject.toml.
