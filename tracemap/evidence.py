"""Traceback → EvidencePack: maps a crash to CodeMap-indexed symbols.

The only module that talks to the CodeMap Python API.  All other TraceMap
modules consume the frozen ``EvidencePack`` dataclass produced here.
"""

from __future__ import annotations

import textwrap
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
    """Failing symbol source signature (qualified_name + signature), or empty string."""

    callers: list[tuple[Frame, Symbol | None]]
    """All mapped frames from the traceback, crash-site first (includes failing_frame)."""

    callees: list[Symbol]
    """Direct callees of the failing symbol."""

    blast_radius: list[tuple[str, int]]
    """(symbol_id, depth) BFS list of every transitive caller, shallowest first."""

    covering_tests: list[Symbol]
    """Test symbols that transitively call the failing symbol."""

    unmapped_frames: list[Frame]
    """Frames whose path was not found in the index."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

    # callees of the failing symbol (direct)
    callees: list[Symbol] = []
    blast_radius: list[tuple[str, int]] = []
    covering_tests: list[Symbol] = []

    if failing_symbol is not None:
        raw_callees = index.outgoing(failing_symbol.id)
        callees = [
            index.symbols[cid]
            for call in raw_callees
            for cid in call.resolved_ids
            if cid in index.symbols
        ]
        blast_radius = index.transitive_callers(failing_symbol.id)
        covering_tests = _tests_covering(index, failing_symbol.id)

    unmapped = [frame for frame, sym in mapped if sym is None]

    source = (
        f"{failing_symbol.qualified_name}{failing_symbol.signature}"
        if failing_symbol is not None
        else ""
    )

    return EvidencePack(
        failing_frame=failing_frame,
        failing_symbol=failing_symbol,
        source=source,
        callers=mapped,
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
    lines.append(
        f"- **file**: `{pack.failing_frame.path}` line {pack.failing_frame.line}"
        f"  (`{pack.failing_frame.name}`)"
    )

    # --- failing symbol ---
    lines.append("\n### Failing Symbol")
    if pack.failing_symbol is not None:
        lines.append(f"- **id**: `{pack.failing_symbol.id}`")
        lines.append(f"- **kind**: {pack.failing_symbol.kind}")
        if pack.source:
            lines.append(f"- **signature**: `{pack.source}`")
    else:
        lines.append("- *(not in index)*")

    # --- call stack ---
    lines.append("\n### Call Stack (crash-site first)")
    for frame, sym in pack.callers:
        sym_label = f"`{sym.qualified_name}`" if sym else "*not in index*"
        lines.append(f"- `{frame.name}` @ `{frame.path}:{frame.line}` → {sym_label}")

    # --- callees ---
    lines.append("\n### Direct Callees")
    if pack.callees:
        for sym in pack.callees:
            lines.append(f"- `{sym.qualified_name}` ({sym.kind})")
    else:
        lines.append("- *(none)*")

    # --- blast radius ---
    lines.append("\n### Blast Radius (transitive callers)")
    if pack.blast_radius:
        for sid, depth in pack.blast_radius[:20]:
            sym = pack.failing_symbol  # placeholder for label
            label = sid
            lines.append(f"- depth {depth}: `{label}`")
        if len(pack.blast_radius) > 20:
            lines.append(f"- … and {len(pack.blast_radius) - 20} more")
    else:
        lines.append("- *(none — function is a leaf entry point)*")

    # --- covering tests ---
    lines.append("\n### Covering Tests")
    if pack.covering_tests:
        for sym in pack.covering_tests:
            lines.append(f"- `{sym.qualified_name}` @ `{sym.path}:{sym.line}`")
    else:
        lines.append("- *(no tests found in blast radius)*")

    # --- unmapped ---
    if pack.unmapped_frames:
        lines.append("\n### Unmapped Frames")
        for frame in pack.unmapped_frames:
            lines.append(f"- `{frame.name}` @ `{frame.path}:{frame.line}`")

    return "\n".join(lines) + "\n"
