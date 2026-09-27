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
