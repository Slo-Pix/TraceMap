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

## Parallel execution

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

## How Bob built TraceMap

Every TraceMap module was designed and written by IBM Bob 2.0 in the sessions above.
Bob is also TraceMap's runtime fix engine: `tracemap fix` hands a CodeMap evidence pack
to the `tracemap-fixer` custom mode via `bobide chat -m tracemap-fixer`, which returns
the patch and the regression test. See `../AGENTS.md`.
