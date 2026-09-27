"""Traceback → EvidencePack: maps a crash to CodeMap-indexed symbols.

The only module that talks to the CodeMap Python API.  All other TraceMap
modules consume the frozen ``EvidencePack`` dataclass produced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from codemap.cache import load_or_build
from codemap.model import CodeIndex, Symbol, is_test_path
from codemap.trace import Frame, map_frames, parse_trace

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidencePack:
    """All CodeMap evidence gathered for one crash."""

    failing_frame: Frame
    """The crash-site frame (innermost, index 0 of the traceback)."""

    failing_symbol: Symbol | None
    """The indexed symbol that owns the failing frame, or None if not in index."""

    source: str
    """Full source text of the failing function (lines symbol.line..symbol.end_line)."""

    call_stack: list[tuple[Frame, Symbol | None]]
    """Mapped traceback frames, crash-site first (what parse_trace returned)."""

    callers: list[Symbol]
    """Direct callers of the failing symbol (from index.incoming)."""

    callees: list[Symbol]
    """Direct callees of the failing symbol."""

    blast_radius: list[tuple[Symbol, int]]
    """(Symbol, depth) BFS list of every transitive caller, shallowest first."""

    covering_tests: list[Symbol]
    """Test symbols that transitively call the failing symbol."""

    unmapped_frames: list[Frame]
    """Frames whose path was not found in the index."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_source(repo: Path, symbol: Symbol) -> str:
    """Read the exact source lines for *symbol* from disk."""
    src_file = repo / symbol.path
    lines = src_file.read_text(encoding="utf-8").splitlines()
    # symbol.line and symbol.end_line are 1-based
    return "\n".join(lines[symbol.line - 1 : symbol.end_line])


def _tests_covering(index: CodeIndex, symbol_id: str) -> list[Symbol]:
    blast = index.transitive_callers(symbol_id)
    return [
        index.symbols[sid]
        for sid, _depth in blast
        if sid in index.symbols
        and index.symbols[sid].kind in {"function", "method"}
        and index.symbols[sid].name.lower().startswith("test")
        and is_test_path(index.symbols[sid].path)
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_evidence(trace_text: str, repo: Path) -> EvidencePack:
    """Index *repo* and map every frame in *trace_text* to CodeMap symbols.

    Parameters
    ----------
    trace_text:
        Raw traceback string (copy-paste from terminal or crash.txt).
    repo:
        Root of the Python project to index.

    Returns
    -------
    EvidencePack
        Frozen dataclass; safe to pickle, cache, or pass between threads.
    """
    index: CodeIndex
    index, _ = load_or_build(str(repo))

    frames = parse_trace(trace_text)
    mapped = map_frames(index, frames)

    failing_frame, failing_symbol = mapped[0] if mapped else (None, None)

    if failing_frame is None:
        raise ValueError("No frames found in the supplied traceback text.")

    # direct callers / callees and wider blast radius
    callers: list[Symbol] = []
    callees: list[Symbol] = []
    blast_radius: list[tuple[str, int]] = []
    covering_tests: list[Symbol] = []

    if failing_symbol is not None:
        callers = [
            index.symbols[call.caller_id]
            for call in index.incoming(failing_symbol.id)
            if call.caller_id is not None and call.caller_id in index.symbols
        ]
        raw_callees = index.outgoing(failing_symbol.id)
        callees = [
            index.symbols[cid]
            for call in raw_callees
            for cid in call.resolved_ids
            if cid in index.symbols
        ]
        raw_blast = index.transitive_callers(failing_symbol.id)
        blast_radius = [
            (index.symbols[sid], depth)
            for sid, depth in raw_blast
            if sid in index.symbols
        ]
        covering_tests = _tests_covering(index, failing_symbol.id)

    unmapped = [frame for frame, sym in mapped if sym is None]

    source = _read_source(repo, failing_symbol) if failing_symbol is not None else ""

    return EvidencePack(
        failing_frame=failing_frame,
        failing_symbol=failing_symbol,
        source=source,
        call_stack=mapped,
        callers=callers,
        callees=callees,
        blast_radius=blast_radius,
        covering_tests=covering_tests,
        unmapped_frames=unmapped,
    )


# ---------------------------------------------------------------------------
# Markdown serialiser (for Bob consumption)
# ---------------------------------------------------------------------------


def render_markdown(pack: EvidencePack) -> str:
    """Return a compact Markdown representation of an ``EvidencePack``."""
    lines: list[str] = []

    lines.append("## TraceMap Evidence Pack\n")

    # --- failing frame ---
    lines.append("### Failing Frame")
    if pack.failing_symbol is not None:
        lines.append(
            f"`{pack.failing_frame.name}` — "
            f"`{pack.failing_symbol.path}:{pack.failing_frame.line}`"
            f" (defined at line {pack.failing_symbol.line})"
        )
    else:
        lines.append(
            f"`{pack.failing_frame.path}` line {pack.failing_frame.line}"
            f"  (`{pack.failing_frame.name}`) — *not in index*"
        )

    # --- source ---
    lines.append("\n### Source of the failing function")
    if pack.source:
        lines.append("```python")
        lines.append(pack.source)
        lines.append("```")
    else:
        lines.append("*(not in index)*")

    # --- direct callers ---
    lines.append("\n### Direct callers")
    if pack.callers:
        for sym in pack.callers:
            lines.append(f"- `{sym.name}` — `{sym.path}:{sym.line}`")
    else:
        lines.append("- *(none)*")

    # --- callees ---
    lines.append("\n### Direct callees")
    if pack.callees:
        for sym in pack.callees:
            lines.append(f"- `{sym.qualified_name}` ({sym.kind})")
    else:
        lines.append("- none")

    # --- blast radius ---
    lines.append("\n### Blast Radius (transitive callers, depth-ranked)")
    if pack.blast_radius:
        lines.append("\n| depth | symbol | path |")
        lines.append("|---|---|---|")
        for sym, depth in pack.blast_radius:
            lines.append(
                f"| {depth} | `{sym.qualified_name}` | `{sym.path}:{sym.line}` |"
            )
    else:
        lines.append("*(none — function is a leaf entry point)*")

    # --- covering tests ---
    lines.append("\n### Covering Tests")
    if pack.covering_tests:
        for sym in pack.covering_tests:
            lines.append(f"- `{sym.qualified_name}` @ `{sym.path}:{sym.line}`")
    else:
        lines.append("- *(no tests found in blast radius)*")

    # --- call stack ---
    lines.append("\n### Call Stack (crash-site first)")
    for frame, sym in pack.call_stack:
        sym_label = f"`{sym.qualified_name}`" if sym else "*not in index*"
        lines.append(f"- `{frame.name}` @ `{frame.path}:{frame.line}` → {sym_label}")

    # --- unmapped ---
    if pack.unmapped_frames:
        lines.append("\n### Unmapped Frames")
        for frame in pack.unmapped_frames:
            lines.append(f"- `{frame.name}` @ `{frame.path}:{frame.line}`")

    return "\n".join(lines) + "\n"
