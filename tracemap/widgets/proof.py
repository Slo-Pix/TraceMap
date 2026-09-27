"""Proof-of-fix modal screen for the TraceMap TUI."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from tracemap.theme import ACCENT, BG, FAIL, MUTED, PANEL, PASS, TEXT, TITLE

__all__ = ["ProofModal"]

DEFAULT_CSS = f"""
ProofModal {{
    align: center middle;
}}

#proof-dialog {{
    width: 84;
    height: 30;
    padding: 1 2;
    border: round {ACCENT};
    background: {PANEL};
    border-title-color: {ACCENT};
    border-title-style: bold;
}}

#proof-scroll {{
    background: {PANEL};
}}

.section-header {{
    color: {TITLE};
    text-style: bold;
    margin-top: 1;
}}

.section-header-fail {{
    color: {FAIL};
    text-style: bold;
    margin-top: 1;
}}

.section-header-pass {{
    color: {PASS};
    text-style: bold;
    margin-top: 1;
}}

.section-body {{
    color: {TEXT};
    background: {BG};
    padding: 0 1;
    margin-bottom: 1;
}}

.section-muted {{
    color: {MUTED};
    background: {BG};
    padding: 0 1;
    margin-bottom: 1;
}}
"""


class ProofModal(ModalScreen[None]):
    """Modal screen that displays proof of a fix: patch diff, before, and after blocks."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("p", "dismiss_modal", "Close"),
    ]

    DEFAULT_CSS = DEFAULT_CSS

    def __init__(self, patch_diff: str, before: str, after: str) -> None:
        super().__init__()
        self._patch_diff = patch_diff
        self._before = before
        self._after = after

    def compose(self) -> ComposeResult:
        with Vertical(id="proof-dialog"):
            self.border_title = "Proof of Fix"
            with VerticalScroll(id="proof-scroll"):
                yield Static("─── PATCH ───", classes="section-header")
                if self._patch_diff:
                    yield Static(self._patch_diff, classes="section-body")
                else:
                    yield Static("No patch — fix is pending.", classes="section-muted")

                yield Static("─── BEFORE (FAIL) ───", classes="section-header-fail")
                yield Static(self._before, classes="section-body")

                yield Static("─── AFTER (PASS) ───", classes="section-header-pass")
                yield Static(self._after, classes="section-body")

    def on_mount(self) -> None:
        self.query_one("#proof-dialog").border_title = "Proof of Fix"

    def action_dismiss_modal(self) -> None:
        """Close the modal."""
        self.dismiss()
