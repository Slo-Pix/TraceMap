"""FramesTable — DataTable widget that renders an EvidencePack's call stack."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.widgets import DataTable

from tracemap.theme import ACCENT, FAIL, MUTED, PANEL, PASS, TEXT

__all__ = ["FramesTable"]


def _rel_path(raw: str, repo: Path | None) -> str:
    """Return *raw* relative to *repo* when possible, else return *raw* unchanged."""
    if repo is None:
        return raw
    try:
        return str(Path(raw).relative_to(repo))
    except ValueError:
        return raw


class FramesTable(DataTable):
    """Renders the call-stack from an EvidencePack, crash-site first.

    Columns: ``#``, ``symbol``, ``file:line``, ``role``, ``indexed``

    - Row 0 (crash frame): symbol name and file:line in FAIL colour, role="crash"
    - Unmapped frames (Symbol is None): frame.name in MUTED for symbol col,
      "not in index" in the indexed col
    - Mapped frames: indexed="✓" in PASS colour
    - Cursor row: ACCENT background, PANEL text (bold) — handled via DEFAULT_CSS
    """

    DEFAULT_CSS = f"""
    FramesTable > .datatable--cursor {{
        background: {ACCENT};
        color: {PANEL};
        text-style: bold;
    }}
    """

    def on_mount(self) -> None:
        """Add columns on first mount."""
        self.cursor_type = "row"
        self.add_columns("#", "symbol", "file:line", "role", "indexed")

    def load_pack(self, pack: EvidencePack, repo: Path | None = None) -> None:
        """Populate the table from an EvidencePack.

        Can be called after mount; clears any existing rows first.

        Parameters
        ----------
        pack:
            The evidence pack whose ``call_stack`` will be displayed.
        repo:
            Project root used to shorten absolute paths to relative ones.
            When ``None``, paths are shown as-is.
        """
        self.clear()

        for idx, (frame, symbol) in enumerate(pack.call_stack):
            is_crash = idx == 0
            rel = _rel_path(frame.path, repo)

            num_cell = Text(str(idx))

            if symbol is None:
                # Unmapped frame: show frame name in symbol col (not "not in index")
                sym_cell = Text(frame.name, style=MUTED)
                file_cell = Text(f"{rel}:{frame.line}", style=MUTED)
                role_cell = Text("crash" if is_crash else "caller", style=MUTED)
                indexed_cell = Text("not in index", style=MUTED)
            elif is_crash:
                # Crash frame — highlight in FAIL
                sym_cell = Text(symbol.qualified_name, style=FAIL)
                file_cell = Text(f"{rel}:{frame.line}", style=FAIL)
                role_cell = Text("crash", style=FAIL)
                indexed_cell = Text("✓", style=PASS)
            else:
                # Normal mapped frame
                sym_cell = Text(symbol.qualified_name, style=TEXT)
                file_cell = Text(f"{rel}:{frame.line}", style=TEXT)
                role_cell = Text("caller", style=TEXT)
                indexed_cell = Text("✓", style=PASS)

            self.add_row(num_cell, sym_cell, file_cell, role_cell, indexed_cell)


# ---------------------------------------------------------------------------
# Import after class definition to avoid circular imports at load time.
# ``from __future__ import annotations`` ensures the annotation in
# load_pack() is treated as a string at parse time, so this is safe.
# ---------------------------------------------------------------------------

from tracemap.evidence import EvidencePack
