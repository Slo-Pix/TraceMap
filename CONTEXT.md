# TraceMap — CONTEXT LOG

## COMMS LOG

| # | Task | Status | Notes |
|---|------|--------|-------|
| task01 | Understand codebase | ✅ DONE | AGENTS.md authored; CodeMap API documented |
| task02 | Flowchart | ✅ DONE | docs/architecture.md, two Mermaid diagrams |
| task03 | Implementation plan | ✅ DONE | docs/bob_plans/task03-implementation-plan.md |
| task04 | evidence.py + render.py | ✅ DONE | parallel subagents; 27 tests passing |
| task05 | tracemap-fixer Skill + mode | ✅ DONE | bob_config/skills/tracemap-fixer/SKILL.md + custom_modes.yaml |
| task06 | engine.py + cli.py + verify.py | ✅ DONE | `invoke_bob` dual-impl (_shell/_handoff), `run_fix`, `tracemap fix`, `run_verify`; `bob` absent → pending handoff; all 27 tests pass |
| task06-fix | blast radius + handoff instruction | ✅ DONE | `blast_radius` changed to `list[tuple[Symbol,int]]`; `render_markdown` emits `| depth \| symbol \| path |` table; terminal render uses `qualified_name`; `_invoke_file_handoff` describes Bob IDE steps + commented-out shell future option; 2 new tests added; 29/29 pass |
| task07 | end-to-end proof | ✅ DONE | crash confirmed real; 3 pre-existing tests pass despite bug; pack built; fix site `average_per_category` (depth-1 caller guard `if not entries: return 0.0`); regression test RED on unpatched / GREEN on patched; `verify.py` bug fixed (`-q`→`-v --override-ini=addopts=`); app exits 0; 4/4 buggy-app tests + 29/29 tracemap tests green; docs/proof.md written |
| task08 | tui.py — Textual TUI | ✅ DONE | 3 subagents in parallel: PipelineRail (widgets/pipeline.py), FramesTable (widgets/frames.py), ProofModal (widgets/proof.py); assembled in tracemap/tui.py (CSS f-string over theme constants, no hex literals); `tracemap` bare invocation launches TUI; `tracemap tui [crash-file]` pre-loads crash; ruff clean; all imports verified |
| task08-fix | TUI pilot bug fixes | ✅ DONE | (1) focus FramesTable on mount so f/x/b/p bindings fire; (2) paths relative to repo root in FramesTable; (3) frame.name in symbol col for unmapped rows, "not in index" moved to indexed col; (4) 3 hardcoded hex literals (#2f2f2f #4a4a4a #9a9a9a) replaced with DIM_TEXT/SCROLL_TRACK/SCROLL_HOVER in theme.py; `load_pack()` gains `repo` param; 5/5 pilot+unit tests pass; 38/38 total green |
