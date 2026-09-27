# TraceMap

**Crash-to-green for Python: paste a failing traceback, get a verified fix.**

TraceMap turns a runtime crash into a proven fix. It uses **CodeMap** (a static
call-graph engine) to map a traceback to the exact failing function — its
callers, callees, blast radius, and the tests that cover it — then hands that
evidence to **IBM Bob 2.0**, which writes the fix and a regression test that
**fails before and passes after**.

Built for the **IBM Bob 2.0 Hackathon** (Sep 25–27, 2026).

## Status

Early prototype — under active development during the hackathon.

## How it works

1. Input a failing traceback (or a failing test / tailed log).
2. CodeMap maps frames → indexed symbols, the failing call chain, blast radius, and affected tests.
3. The evidence pack is handed to IBM Bob 2.0 (Agent mode).
4. Bob writes a root-cause fix + a regression test.
5. TraceMap runs the affected tests to verify **fail-before / pass-after**.

## Built on

- [CodeMap](https://github.com/Slo-Pix/codemap) — pre-existing open-source static call-graph engine by the author, used here as a dependency.
- IBM Bob 2.0 — the reasoning/acting agent that writes and verifies the fix.

## License

MIT




Read the CodeMap repository in @codemap-ref and explain how it works. I am building a new tool on
top of it and need its real API, not its README claims.

Answer specifically:
1. How does a raw Python traceback become mapped symbols? Name the exact functions and their
   signatures, and say what order the frames come back in.
2. How do I get a function's callers, callees, and full transitive blast radius from an index?
3. How do I find which tests cover a symbol?
4. Which CLI subcommands support --json, and which do not?

Then run /init and write tracemap/AGENTS.md capturing:
- GOAL: TraceMap = crash -> CodeMap evidence pack -> Bob writes a verified fix + regression test
  that FAILS BEFORE and PASSES AFTER.
- CodeMap (Apache-2.0) is a PRE-EXISTING read-only dependency. TraceMap is the new hackathon build.
  Never edit CodeMap's source.
- The exact library API you just found, as a code block. Record that `codemap trace/impact/refs`
  have NO --json flag, so we use the Python API and never shell out.
- LAYOUT: workspace root is /home/slopixel/lablab; the repo is tracemap/; the package is
  tracemap/tracemap/. Never create files outside tracemap/.
- SCOPE: TraceMap is Python-only end to end (pytest is the only runner wired).
- CONVENTIONS: Python 3.11+, pytest, MIT, small typed modules, colours only from
  tracemap/tracemap/theme.py.
- HARD RULE: every fix ships a regression test that fails before and passes after.

After finishing output results to global Context file - Context.md
