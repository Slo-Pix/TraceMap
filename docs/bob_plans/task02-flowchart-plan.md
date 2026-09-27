# task02 — Create a Flowchart — Plan

## Top-Level Overview

**Goal:** Produce `tracemap/docs/architecture.md` containing two valid Mermaid diagrams grounded in the actual CodeMap source code, then append a COMMS LOG entry to `CONTEXT.md`.

**Scope:**
- Diagram 1: Internal CodeMap pipeline — real function names from `trace.py`, `indexer.py`, `model.py`, `graph.py`, and `affected.py`.
- Diagram 2: TraceMap end-to-end system — three actor lanes: CodeMap (deterministic), IBM Bob (reasoning), TraceMap harness.
- No new Python code; no changes to existing tracemap source files.

**Approach:** Write `tracemap/docs/architecture.md` from scratch, then append one line to `CONTEXT.md`.

---

## Sub-Tasks

### Sub-Task 1 — Gather real function names from codemap-ref source

**Intent:** Confirm the exact function names and data types that must appear in Diagram 1 so the flowchart matches the real code and is not invented.

**Expected Outcomes:**
- A confirmed list of the real symbols used in the CodeMap trace-to-evidence pipeline, in order.

**Todo List:**
- [x] Read `codemap-ref/src/codemap/trace.py` → confirm `parse_trace()`, `map_frames()`
- [x] Read `codemap-ref/src/codemap/indexer.py` → confirm `build_index()`, `_source_files()`, `resolve_calls()`
- [x] Read `codemap-ref/src/codemap/model.py` → confirm `CodeIndex`, `Symbol`, `Frame`, `incoming()`, `outgoing()`, `transitive_callers()`
- [x] Read `codemap-ref/src/codemap/graph.py` → confirm `call_forest()`, `to_html()`
- [x] Read `codemap-ref/src/codemap/affected.py` → confirm `affected_tests()`, `_is_test_symbol()`

**Relevant Context:**
- `codemap-ref/src/codemap/trace.py` — `parse_trace(text) -> list[Frame]`, `map_frames(index, frames) -> list[tuple[Frame, Symbol | None]]`
- `codemap-ref/src/codemap/indexer.py` — `build_index(path) -> CodeIndex`
- `codemap-ref/src/codemap/model.py` — `CodeIndex.incoming()`, `CodeIndex.outgoing()`, `CodeIndex.transitive_callers()`
- `codemap-ref/src/codemap/affected.py` — `affected_tests(root, range_spec)`

**Status:** [x] done (researched via subagent before writing this plan)

---

### Sub-Task 2 — Write `tracemap/docs/architecture.md` with two Mermaid diagrams

**Intent:** Produce the artifact file. Both diagrams must be valid Mermaid (no double quotes inside `[]`, no raw parentheses inside `[]`), use real function names, and have one descriptive sentence each.

**Expected Outcomes:**
- File `tracemap/docs/architecture.md` exists.
- Diagram 1 (`flowchart TD`) charts the exact CodeMap control flow: raw traceback text → `parse_trace()` → `list[Frame]` → `build_index()` → `CodeIndex` → `map_frames()` → matched `Symbol` → `incoming()` / `outgoing()` → callers/callees → `transitive_callers()` → blast radius → optional `_is_test_symbol()` filter → covering tests.
- Diagram 2 (`flowchart LR` with subgraphs) shows three labelled actor lanes — `CodeMap [deterministic]`, `IBM Bob [reasoning]`, `TraceMap [harness]` — with the crash-to-proof flow across them.
- Both diagrams render correctly in a Mermaid renderer.
- One sentence of prose appears immediately after each diagram.

**Todo List:**
- [ ] Create `tracemap/docs/` directory if absent (it exists but is empty).
- [ ] Write `tracemap/docs/architecture.md`:
  - Add H1 heading `# TraceMap — Architecture`.
  - Add H2 `## Diagram 1 — How CodeMap turns a traceback into evidence`.
  - Write the `flowchart TD` Mermaid block using real function names (see Relevant Context below).
  - Add the one-sentence explanation.
  - Add H2 `## Diagram 2 — TraceMap end to end`.
  - Write the `flowchart LR` Mermaid block with three subgraph actor lanes.
  - Add the one-sentence explanation.

**Relevant Context — Diagram 1 node sequence (real names):**

```
raw traceback text
  → parse_trace(text) [trace.py]           returns list[Frame]
  → build_index(path) [indexer.py]         returns CodeIndex (scan + _source_files + resolve_calls)
  → map_frames(index, frames) [trace.py]   returns list[tuple[Frame, Symbol|None]]
  → matched Symbol
  → CodeIndex.incoming(symbol_id)          callers
  → CodeIndex.outgoing(symbol_id)          callees
  → CodeIndex.transitive_callers(symbol_id) blast radius BFS
  → filter _is_test_symbol [affected.py]  covering tests
```

**Relevant Context — Diagram 2 actor lanes:**

| Actor | Boxes |
|---|---|
| TraceMap harness | receive crash / traceback, call CodeMap API, assemble evidence pack, run affected tests, emit proof artifact |
| CodeMap deterministic | `parse_trace` + `map_frames`, `build_index`, `transitive_callers`, `affected_tests` |
| IBM Bob reasoning | read evidence pack (Agent mode), write fix patch, write regression test, iterate on test failures |

**Status:** [ ] pending

---

### Sub-Task 3 — Append COMMS LOG entry to `CONTEXT.md`

**Intent:** Record task02 completion in the shared coordination file, as required by the prompt's FINISH instruction.

**Expected Outcomes:**
- A single new line is appended to the `COMMS LOG` section in `CONTEXT.md`.
- Format: `[+] [2026-09-27 - BOB] task02 complete. Produced tracemap/docs/architecture.md: two Mermaid diagrams — CodeMap internal pipeline (real function names) and TraceMap end-to-end actor lanes. Both render valid Mermaid.`

**Todo List:**
- [ ] Append the COMMS LOG line to `CONTEXT.md`.

**Relevant Context:**
- `CONTEXT.md` COMMS LOG section ends at line 146 (`----x----x----x----x----x----`).
- Append format: `[+] [DATE - BOB] message`.

**Status:** [ ] pending
