"""Terminal rendering of an EvidencePack using Rich.

All colours come exclusively from ``tracemap.theme`` — no hex literals here.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tracemap.evidence import EvidencePack
from tracemap.theme import (
    ACCENT,
    FAIL,
    INFO,
    MUTED,
    PASS,
    TEXT,
    TITLE,
    WARN,
)

__all__ = ["render_pack"]


def _section_title(text: str) -> Text:
    t = Text(text, style=f"bold {TITLE}")
    return t


def render_pack(pack: EvidencePack, *, console: Console | None = None) -> None:
    """Print a rich-formatted EvidencePack to the terminal.

    Parameters
    ----------
    pack:
        The evidence to display.
    console:
        Optional Rich ``Console`` instance; a default stderr console is
        created when *None*.
    """
    if console is None:
        console = Console(highlight=False)

    # ── Header ──────────────────────────────────────────────────────────────
    header = Text()
    header.append("TraceMap", style=f"bold {ACCENT}")
    header.append(" — Evidence Pack", style=f"bold {TITLE}")
    console.print(Panel(header, border_style=ACCENT))

    # ── Failing frame ───────────────────────────────────────────────────────
    console.print(_section_title("Failing Frame"))
    frame_text = Text()
    frame_text.append(f"{pack.failing_frame.name}", style=f"bold {FAIL}")
    frame_text.append(f"  {pack.failing_frame.path}", style=TEXT)
    frame_text.append(f":{pack.failing_frame.line}", style=f"bold {FAIL}")
    console.print(frame_text)

    # ── Failing symbol ──────────────────────────────────────────────────────
    console.print()
    console.print(_section_title("Failing Symbol"))
    if pack.failing_symbol is not None:
        sym_text = Text()
        sym_text.append(pack.failing_symbol.qualified_name, style=f"bold {FAIL}")
        if pack.source:
            sym_text.append(f"  {pack.failing_symbol.signature}", style=MUTED)
        sym_text.append(
            f"  ({pack.failing_symbol.kind}  line {pack.failing_symbol.line})",
            style=MUTED,
        )
        console.print(sym_text)
    else:
        console.print(Text("(not in index)", style=MUTED))

    # ── Call stack ──────────────────────────────────────────────────────────
    console.print()
    console.print(_section_title("Call Stack  (crash-site first)"))
    stack_table = Table(show_header=False, box=None, padding=(0, 1))
    for i, (frame, sym) in enumerate(pack.callers):
        depth_marker = Text(f"[{i}]", style=MUTED)
        fn_text = Text(frame.name, style=f"bold {FAIL}" if i == 0 else f"bold {WARN}")
        loc_text = Text(f"{frame.path}:{frame.line}", style=MUTED)
        sym_text = (
            Text(sym.qualified_name, style=INFO)
            if sym is not None
            else Text("not in index", style=MUTED)
        )
        stack_table.add_row(depth_marker, fn_text, loc_text, sym_text)
    console.print(stack_table)

    # ── Blast radius ────────────────────────────────────────────────────────
    console.print()
    console.print(_section_title(f"Blast Radius  ({len(pack.blast_radius)} transitive callers)"))
    if pack.blast_radius:
        br_table = Table(show_header=False, box=None, padding=(0, 1))
        for sid, depth in pack.blast_radius[:15]:
            br_table.add_row(
                Text(f"depth {depth}", style=MUTED),
                Text(sid, style=INFO),
            )
        if len(pack.blast_radius) > 15:
            console.print(
                Text(f"  … and {len(pack.blast_radius) - 15} more", style=MUTED)
            )
        console.print(br_table)
    else:
        console.print(Text("  (leaf — no callers)", style=MUTED))

    # ── Covering tests ──────────────────────────────────────────────────────
    console.print()
    console.print(_section_title(f"Covering Tests  ({len(pack.covering_tests)} found)"))
    if pack.covering_tests:
        for sym in pack.covering_tests:
            t = Text()
            t.append(sym.qualified_name, style=f"bold {PASS}")
            t.append(f"  {sym.path}:{sym.line}", style=MUTED)
            console.print(t)
    else:
        console.print(Text("  (none found in blast radius)", style=MUTED))

    # ── Unmapped frames ─────────────────────────────────────────────────────
    if pack.unmapped_frames:
        console.print()
        console.print(_section_title(f"Unmapped Frames  ({len(pack.unmapped_frames)})"))
        for frame in pack.unmapped_frames:
            t = Text()
            t.append(frame.name, style=MUTED)
            t.append(f"  {frame.path}:{frame.line}", style=MUTED)
            console.print(t)
