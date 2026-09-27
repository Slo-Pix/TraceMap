# TraceMap End-to-End Proof

**Claim:** a crash becomes a verified fix — failing traceback in, green test suite out.

All terminal output below was produced live during task07; nothing is fabricated.

---

## 1. The crash (STEP 1c)

```
$ cd tracemap && python -m examples.buggy_app.main
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
EXIT:1
```

---

## 2. Pre-existing tests pass despite the crash (STEP 1d)

This is the test gap TraceMap closes: the test suite is green while the application crashes.

```
$ cd tracemap && python -m pytest examples/buggy_app/tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/slopixel/lablab/tracemap
configfile: pyproject.toml
collected 3 items

examples/buggy_app/tests/test_report.py ...                              [100%]

============================== 3 passed in 0.03s ==============================
```

All 3 tests pass. The crash is not caught by any existing test because they use a
`POPULATED` fixture that includes a `training` entry — they never exercise the
empty-category path.

---

## 3. Evidence pack summary (STEP 1b — `tracemap fix` output)

```
$ cd tracemap && tracemap fix examples/buggy_app/crash.txt

◐ Reading traceback …
 ✓ Repo root: /home/slopixel/lablab/tracemap
 ◐ Indexing repo and mapping frames …
 ✓ Evidence built — failing symbol: divide_total
```

**Failing symbol:** `divide_total` — `examples/buggy_app/report.py` line 8

**Direct callers (from pack.md):**
```
- `average_per_category` — `examples/buggy_app/report.py:13`
- `overall_average`      — `examples/buggy_app/report.py:19`
```

**Blast radius (from pack.md):**

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

---

## 4. Diagnosis and patch diff (STEP 2)

### Diagnosis

**Exception:** `ZeroDivisionError: division by zero`
**Expression:** `total / count` at `divide_total` line 10
**Precondition violated:** `count == 0`

**Root cause:** `summarize_expenses` iterates over all `CATEGORIES` (including `"training"`).
`entries_for(expenses, "training")` returns `[]` because no training expense was filed this
period. `average_per_category([])` passes `len([]) == 0` to `divide_total`, which divides
by zero.

**Fix site decision (from evidence pack):**

`divide_total`'s contract is "average of total spread over count entries" — it makes no
promise about handling zero count. Its direct callers (depth-1 in the blast radius) are
`average_per_category` and `overall_average`. `overall_average` always passes the full
expense list, which is never empty in practice. `average_per_category` receives the filtered
list per category, and an empty list is a normal application condition (a category with no
filings). The fix belongs in `average_per_category`: guard against the empty case before
calling into `divide_total`, returning `0.0` to signal "no spend in this category".

**Patch:** add an early-return guard in `average_per_category`
(`examples/buggy_app/report.py`, line 14):

```diff
 def average_per_category(entries: list[dict[str, object]]) -> float:
     """Mean amount across one category's entries."""
+    if not entries:
+        return 0.0
     total = sum(float(entry["amount"]) for entry in entries)
     return divide_total(total, len(entries))
```

---

## 5. Regression test source (STEP 2)

Appended to `examples/buggy_app/tests/test_report.py`:

```python
def test_average_per_category_empty_entries_returns_zero():
    """average_per_category([]) must return 0.0, not raise ZeroDivisionError.

    Regression for: ZeroDivisionError in divide_total when a category has no
    expense records (e.g. 'training' in the real dataset).
    Fix site: average_per_category — guard added before calling divide_total.
    """
    assert average_per_category([]) == 0.0
```

---

## 6. Regression test FAILING on original (unpatched) code (STEP 3)

```
$ cd tracemap && git stash -- examples/buggy_app/report.py
$ python -m pytest examples/buggy_app/tests/test_report.py::test_average_per_category_empty_entries_returns_zero -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/slopixel/lablab/tracemap
configfile: pyproject.toml
collected 1 item

examples/buggy_app/tests/test_report.py F                                [100%]

=================================== FAILURES ===================================
_____________ test_average_per_category_empty_entries_returns_zero _____________

    def test_average_per_category_empty_entries_returns_zero():
        ...
>       assert average_per_category([]) == 0.0
               ^^^^^^^^^^^^^^^^^^^^^^^^

examples/buggy_app/tests/test_report.py:37:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
examples/buggy_app/report.py:16: in average_per_category
    return divide_total(total, len(entries))
examples/buggy_app/report.py:10: in divide_total
    return total / count
           ~~~~~~^~~~~~~
E       ZeroDivisionError: division by zero

FAILED examples/buggy_app/tests/test_report.py::test_average_per_category_empty_entries_returns_zero
============================== 1 failed in 0.02s ==============================
EXIT:1

$ git stash pop
```

---

## 7. Full suite green after patch (STEP 3)

### via verify.py

```python
from pathlib import Path
from tracemap.verify import run_verify

result = run_verify(Path('.'), ['examples/buggy_app/tests/test_report.py'])
# passed_after: ['...::test_average_per_category',
#                '...::test_overall_average',
#                '...::test_summarize_every_category_present',
#                '...::test_average_per_category_empty_entries_returns_zero']
# failed_after: []
# ok: True
```

```
passed_after: ['examples/buggy_app/tests/test_report.py::test_average_per_category',
               'examples/buggy_app/tests/test_report.py::test_overall_average',
               'examples/buggy_app/tests/test_report.py::test_summarize_every_category_present',
               'examples/buggy_app/tests/test_report.py::test_average_per_category_empty_entries_returns_zero']
failed_after: []
ok: True
```

### pytest directly

```
$ cd tracemap && python -m pytest examples/buggy_app/tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/slopixel/lablab/tracemap
configfile: pyproject.toml
collected 4 items

examples/buggy_app/tests/test_report.py ....                             [100%]

============================== 4 passed in 0.01s ==============================
EXIT:0
```

### TraceMap's own test suite (29 tests, all green)

```
$ cd tracemap && python -m pytest tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/slopixel/lablab/tracemap
configfile: pyproject.toml
collected 29 items

tests/test_evidence.py .............................                      [100%]

============================== 29 passed in 0.05s ==============================
```

---

## 8. Application runs to completion, exit 0 (STEP 3)

```
$ cd tracemap && python -m examples.buggy_app.main
travel        250.00
meals          42.50
hardware     1299.00
training        0.00
ALL           460.38
EXIT:0
```

The crash is gone. `training` correctly shows `0.00` (no filings this period).
Every pre-existing test still passes. The regression test is red before and green after.

---

## Summary

| Item | Result |
|---|---|
| Root cause | `average_per_category` passes `len([]) == 0` to `divide_total` when a category has no filings |
| Fix site | `average_per_category` — 2-line guard (`if not entries: return 0.0`) |
| Patch | `examples/buggy_app/report.py` lines 15-16 inserted |
| Regression test | `test_average_per_category_empty_entries_returns_zero` — RED before / GREEN after |
| Blast radius | 8 transitive callers checked — all green |
| verify.py bug found | `_pytest_json` used `-q` which emits dots not `PASSED`/`FAILED` lines; fixed by switching to `-v --override-ini=addopts=` |
