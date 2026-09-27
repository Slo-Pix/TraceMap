# TraceMap Evidence Pack

**Exception:** `ZeroDivisionError: division by zero`

## Failing frame

`divide_total` — `examples/buggy_app/report.py:10` (defined at line 8)

## Source of the failing function

```python
def divide_total(total: float, count: int) -> float:
    """Average of `total` spread over `count` entries."""
    return total / count
```

## Direct callers

- `average_per_category` — `examples/buggy_app/report.py:13`
- `overall_average` — `examples/buggy_app/report.py:19`

## Direct callees

- none

## Blast radius (transitive callers, depth-ranked)

| depth | symbol | path |
|---|---|---|
| 1 | `overall_average` | `examples/buggy_app/report.py:19` |
| 1 | `average_per_category` | `examples/buggy_app/report.py:13` |
| 2 | `test_overall_average` | `examples/buggy_app/tests/test_report.py:20` |
| 2 | `build_report` | `examples/buggy_app/report.py:33` |
| 2 | `test_average_per_category` | `examples/buggy_app/tests/test_report.py:16` |
| 2 | `summarize_expenses` | `examples/buggy_app/report.py:25` |
| 3 | `main` | `examples/buggy_app/main.py:9` |
| 3 | `test_summarize_every_category_present` | `examples/buggy_app/tests/test_report.py:24` |

## Tests covering the blast radius

- `examples/buggy_app/tests/test_report.py::test_overall_average` — **currently PASSES despite the bug**
- `examples/buggy_app/tests/test_report.py::test_average_per_category` — **currently PASSES despite the bug**
- `examples/buggy_app/tests/test_report.py::test_summarize_every_category_present` — **currently PASSES despite the bug**

## Frames not in index

- `<module>` at `/home/slopixel/lablab/tracemap/examples/buggy_app/main.py:14` — not indexed (outside the repo)
- `_run_code` at `<frozen runpy>:88` — not indexed (outside the repo)
- `_run_module_as_main` at `<frozen runpy>:198` — not indexed (outside the repo)

## Full traceback

```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/slopixel/lablab/tracemap/examples/buggy_app/main.py", line 14, in <module>
    main()
  File "/home/slopixel/lablab/tracemap/examples/buggy_app/main.py", line 10, in main
    print(build_report(load_expenses()))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/slopixel/lablab/tracemap/examples/buggy_app/report.py", line 35, in build_report
    averages = summarize_expenses(expenses)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/slopixel/lablab/tracemap/examples/buggy_app/report.py", line 28, in summarize_expenses
    category: average_per_category(entries_for(expenses, category))
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/slopixel/lablab/tracemap/examples/buggy_app/report.py", line 16, in average_per_category
    return divide_total(total, len(entries))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/slopixel/lablab/tracemap/examples/buggy_app/report.py", line 10, in divide_total
    return total / count
           ~~~~~~^~~~~~~
ZeroDivisionError: division by zero
```
