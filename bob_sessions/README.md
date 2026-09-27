# IBM Bob 2.0 — Task Session Summaries

Required hackathon evidence: one session-consumption summary per Bob task.
Each screenshot shows the task title, its Bobcoin cost, and the context breakdown.

| Task | Bob capability | Cost | Screenshot |
|------|----------------|------|------------|
| task01 | understand codebase | 1.13 | `tracemap_task01_understand_codebase_summary.png` |
| task02 | create a flowchart | 1.02 | `tracemap_task02_flowchart_summary.png` |
| task03 | create implementation plan (Plan mode) | 0.96 | `tracemap_task03_implementation_plan_summary.png` |
| task02+03 | **parallel tasks** | — | `tracemap_task02_03_parallel_tasks_evidence.png` |
| task04 | build feature + iterative debugging | 2.70 | `tracemap_task04_evidence_pack_rootcause_summary.png` |
| task05 | **work with skills** — authored the runtime fix engine | 1.98 | `tracemap_task05_skills_fixer_mode_summary.png` |
| task06+07 | **build feature** — fix engine, CLI, and the end-to-end proof | 13.27 | `tracemap_task06_07_engine_and_proof_summary.png` |
| task08 | **build feature** — the Textual TUI | 9.71 | `tracemap_task08_tui_build_summary.png` |
| task08 | **parallel agents** — three subagents, one per TUI widget | (same task) | `tracemap_task08_parallel_subagents_fanout.png` |
| task10 | **document understanding** — README, docstrings, commit | 3.14 | `tracemap_task10_docs_and_docstrings_summary.png` |

## Parallel execution

TraceMap's build used Bob's parallelism at both levels.

**Subagent fan-out within one task.** `tracemap_task08_parallel_subagents_fanout.png`
shows three subagents running concurrently, each owning one TUI widget and each with its
own tool count and cost:

```
Dispatch subagent A — widgets/pipeline.py (PipelineRail widget)
  Write widgets/pipeline.py   Done ·  7 tools · 15.5k · 0.198 ·   46s
  Write widgets/proof.py      Done · 13 tools · 17.3k · 0.395 ·   53s
  Write widgets/frames.py     Done · 16 tools · 25.2k · 0.552 · 1m 5s
All three widgets are built. Now let me read them to verify before assembling tui.py
```

Three agents, 1.145 coins and ~65 seconds of wall clock for work that would have run
close to two and a half minutes in sequence. The split is real rather than staged: the
three widgets share no files, so they could be written simultaneously and assembled
afterwards — which is exactly what the parent task then did.

**Concurrent top-level tasks.**

`tracemap_task02_03_parallel_tasks_evidence.png` shows two Bob tasks running
concurrently — the flowchart task and the Plan-mode design task — while task01 sits
completed above them. TraceMap's build overlapped independent work this way throughout.

## Iterative debugging, not one-shot generation

`tracemap_task04_evidence_pack_rootcause_summary.png` is the more interesting artifact.
After Bob built `evidence.py`, running it against the real crash exposed two defects:
`source` was a broken string concatenation that omitted the buggy line entirely, and
`callers` held traceback frames rather than the function's actual callers. The screenshot
captures Bob diagnosing both to root cause and repairing them — then adding regression
tests so neither can return silently. Test count went 19 → 27.

That loop — build, run against reality, diagnose, repair, guard — is the same loop
TraceMap automates for its users.

## Bob authored its own runtime engine

`tracemap_task05_skills_fixer_mode_summary.png` shows Bob authoring the `tracemap-fixer`
custom mode and Skill — an 8-step fix contract (parse → diagnose → read → plan → apply →
regression test → verify → report) that Bob itself then executes at TraceMap's runtime.

The screenshot captures the dry-run against a real evidence pack. Note where it chose to
patch:

```
ROOT CAUSE:   average_per_category passes len(entries) with no empty-list guard;
              summarize_expenses calls it for every category absent from the dataset
PATCH:        examples/buggy_app/report.py:15 — guard at the top of average_per_category
REGRESSION:   test_average_per_category_empty_entries_returns_zero
BLAST RADIUS: 8 callers checked — all green; application runs to completion.
```

The crash surfaced in `divide_total`, but the defect was one frame up. Bob used the
evidence pack's caller list to locate the real fix site — and the Skill requires re-running
the original failing command and checking the exit code, so a patch that merely changes
which exception fires is rejected.

## The proof session

`tracemap_task06_07_engine_and_proof_summary.png` is the single largest session of the
build (13.27 coins, 96k context, 11 files changed). It covers `engine.py`, `verify.py`,
`cli.py`, and the end-to-end proof in `../docs/proof.md`.

Bob located the fix one frame ABOVE the crash. The traceback raised in `divide_total`,
but the defect was in its caller: `average_per_category` passed `len([])` whenever
`summarize_expenses` requested a category with no records. Bob read the evidence pack's
Direct Callers and Blast Radius sections, patched the caller with a two-line guard, and
wrote `test_average_per_category_empty_entries_returns_zero`.

Verified independently by reverting the patch and re-running the test:

```
report.py reverted to unpatched:
    E   ZeroDivisionError: division by zero
    FAILED test_average_per_category_empty_entries_returns_zero
patch restored:
    ....  [100%]  all tests pass
```

The application now exits 0 and prints `training 0.00` instead of crashing.

## How Bob built TraceMap

Every TraceMap module was designed and written by IBM Bob 2.0 in the sessions above.
Bob is also TraceMap's runtime fix engine: `tracemap fix` hands a CodeMap evidence pack
to the `tracemap-fixer` custom mode via `bobide chat -m tracemap-fixer`, which returns
the patch and the regression test. See `../AGENTS.md`.
