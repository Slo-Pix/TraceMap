"""TraceMap — crash to green  (Textual TUI).

Launch with ``tracemap`` (no arguments) or ``tracemap tui``.

Layout
------
LEFT RAIL (width 36)   PIPELINE     — 5 live-updated pipeline stages
MAIN TOP  (height 3)   TRACEBACK    — paste / load a traceback
MAIN      (1fr)        FRAMES       — DataTable, crash-site first
INSPECTOR (height 18)  INSPECTOR    — source, callers/callees, blast radius
MODAL                  PROOF        — patch diff + before/after blocks

Keys
----
t  paste trace        x  expand inspector   b  blast radius
f  run Bob fix        p  proof              v/enter  open in editor
?  help               ctrl+d  quit
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, OptionList, Static

from tracemap.theme import (
    ACCENT,
    BG,
    BORDER,
    DIM_TEXT,
    HOVER,
    INFO,
    MUTED,
    PANEL,
    PASS,
    SCROLL_HOVER,
    SCROLL_TRACK,
    TEXT,
    TITLE,
    WARN,
)
from tracemap.widgets.frames import FramesTable
from tracemap.widgets.pipeline import PipelineRail
from tracemap.widgets.proof import ProofModal

# ---------------------------------------------------------------------------
# CSS — built as an f-string so every colour comes from theme constants
# ---------------------------------------------------------------------------

_CSS = f"""
Screen {{
    background: {BG};
    color: {TEXT};
}}
* {{
    scrollbar-color: {SCROLL_TRACK};
    scrollbar-color-hover: {SCROLL_HOVER};
    scrollbar-color-active: {ACCENT};
    scrollbar-background: {PANEL};
    scrollbar-background-hover: {PANEL};
    scrollbar-background-active: {PANEL};
    scrollbar-size-vertical: 1;
}}

/* ── body ──────────────────────────────────────────────────────────────── */
#body {{
    height: 1fr;
    padding: 1 1 0 1;
}}

/* ── pipeline rail ─────────────────────────────────────────────────────── */
#pipeline-panel {{
    width: 36;
    height: 1fr;
    margin: 0 1 1 0;
    border: round {BORDER};
    background: {PANEL};
    border-title-color: {TITLE};
    border-title-style: bold;
}}
#pipeline-panel:focus-within {{
    border: round {ACCENT};
    border-title-color: {ACCENT};
}}

/* ── main column ───────────────────────────────────────────────────────── */
#main {{
    width: 1fr;
    height: 1fr;
}}

/* ── traceback input ────────────────────────────────────────────────────── */
#trace-panel {{
    height: 3;
    padding: 0 1;
    border: round {BORDER};
    background: {PANEL};
    border-title-color: {TITLE};
    border-title-style: bold;
}}
#trace-panel:focus-within {{
    border: round {ACCENT};
    border-title-color: {ACCENT};
}}
#trace-input {{
    width: 1fr;
    height: 1;
    border: none;
    padding: 0;
    background: {PANEL};
    color: {TEXT};
}}

/* ── frames table ───────────────────────────────────────────────────────── */
#frames-panel {{
    height: 1fr;
    margin: 1 0;
    border: round {BORDER};
    background: {PANEL};
    border-title-color: {TITLE};
    border-title-style: bold;
    border-subtitle-color: {MUTED};
}}
#frames-panel:focus-within {{
    border: round {ACCENT};
    border-title-color: {ACCENT};
}}
FramesTable {{
    height: 1fr;
    background: {PANEL};
}}
DataTable > .datatable--header {{
    background: {PANEL};
    color: {DIM_TEXT};
    text-style: bold;
}}
DataTable > .datatable--cursor {{
    background: {ACCENT};
    color: {PANEL};
    text-style: bold;
}}
DataTable > .datatable--hover {{
    background: {HOVER};
}}

/* ── inspector ──────────────────────────────────────────────────────────── */
#inspector {{
    display: none;
    height: 18;
    padding: 0 2;
    margin: 0 0 1 0;
    border: round {BORDER};
    background: {PANEL};
    border-title-color: {TITLE};
    border-title-style: bold;
    border-subtitle-color: {MUTED};
}}
#inspector:focus-within {{
    border: round {ACCENT};
    border-title-color: {ACCENT};
}}
#inspector-details {{
    height: auto;
}}
#details-scroll {{
    height: auto;
    max-height: 9;
    margin-top: 1;
}}
#relations {{
    height: 1fr;
    min-height: 3;
    margin-top: 1;
    padding: 0;
    border: none;
    background: {PANEL};
}}
#relations:focus {{
    border: none;
}}
OptionList > .option-list--option-highlighted {{
    background: {ACCENT};
    color: {PANEL};
    text-style: bold;
}}
OptionList > .option-list--option-hover {{
    background: {HOVER};
}}

/* ── modals ─────────────────────────────────────────────────────────────── */
TraceScreen {{
    align: center middle;
}}
HelpScreen {{
    align: center middle;
}}
#trace-dialog {{
    width: 84;
    height: 24;
    padding: 1 2;
    border: round {ACCENT};
    background: {PANEL};
    border-title-color: {ACCENT};
    border-title-style: bold;
}}
#trace-text {{
    height: 1fr;
    margin: 1 0;
    background: {BG};
}}
#trace-hint {{
    color: {MUTED};
}}
#help-panel {{
    width: 64;
    height: auto;
    padding: 1 2;
    border: round {ACCENT};
    background: {PANEL};
    border-title-color: {ACCENT};
    border-title-style: bold;
    border-subtitle-color: {MUTED};
}}
#help-body {{
    height: auto;
    color: {TEXT};
}}
"""

# ---------------------------------------------------------------------------
# Help screen
# ---------------------------------------------------------------------------

_HELP_SECTIONS = (
    (
        "Trace",
        (
            ("t", "paste / load a traceback"),
            ("f", "run the Bob fix (drives pipeline live)"),
        ),
    ),
    (
        "Navigation",
        (
            ("x", "toggle inspector panel"),
            ("b", "show blast radius"),
            ("v / enter", "open crash file in editor"),
            ("p", "show proof-of-fix modal"),
        ),
    ),
    (
        "App",
        (
            ("?", "show this help"),
            ("ctrl+d", "quit"),
        ),
    ),
)


class HelpScreen(ModalScreen[None]):
    """Key-binding reference modal."""

    BINDINGS: ClassVar[list[Binding]] = [Binding("escape", "dismiss_help", "Close")]

    DEFAULT_CSS = f"""
    HelpScreen {{ align: center middle; }}
    #help-panel {{
        width: 64;
        height: auto;
        padding: 1 2;
        border: round {ACCENT};
        background: {PANEL};
        border-title-color: {ACCENT};
        border-title-style: bold;
    }}
    #help-body {{ height: auto; color: {TEXT}; }}
    """

    def compose(self) -> ComposeResult:
        """Build the help panel with key-binding sections."""
        lines: list[str] = []
        for section_title, bindings in _HELP_SECTIONS:
            lines.append(f"[bold {TITLE}]{section_title}[/]\n")
            for key, desc in bindings:
                lines.append(f"  [{ACCENT}]{key:<14}[/] [{MUTED}]{desc}[/]\n")
            lines.append("")
        content = "".join(lines)

        panel = Vertical(Static(content, id="help-body"), id="help-panel")
        panel.border_title = "Help"
        yield panel

    def action_dismiss_help(self) -> None:
        """Close the help modal."""
        self.dismiss()


# ---------------------------------------------------------------------------
# Trace paste modal
# ---------------------------------------------------------------------------


class TraceScreen(ModalScreen[str | None]):
    """Modal for pasting a raw traceback."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+s", "submit_trace", "Load trace"),
        Binding("escape", "cancel_trace", "Cancel"),
    ]

    DEFAULT_CSS = f"""
    TraceScreen {{ align: center middle; }}
    #trace-dialog {{
        width: 84;
        height: 24;
        padding: 1 2;
        border: round {ACCENT};
        background: {PANEL};
        border-title-color: {ACCENT};
        border-title-style: bold;
    }}
    #trace-text {{
        height: 1fr;
        margin: 1 0;
        background: {BG};
    }}
    #trace-hint {{ color: {MUTED}; }}
    """

    def compose(self) -> ComposeResult:
        """Build the trace-paste dialog."""
        dialog = Vertical(
            Input(placeholder="Paste traceback here…", id="trace-text"),
            Static("ctrl+s to load  ·  escape to cancel", id="trace-hint"),
            id="trace-dialog",
        )
        dialog.border_title = "Paste Traceback"
        yield dialog

    def on_mount(self) -> None:
        """Focus the text input on open."""
        self.query_one("#trace-text", Input).focus()

    def action_submit_trace(self) -> None:
        """Dismiss with the entered text, or None if empty."""
        value = self.query_one("#trace-text", Input).value.strip()
        self.dismiss(value or None)

    def action_cancel_trace(self) -> None:
        """Dismiss without loading a trace."""
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


class TraceMapApp(App[None]):
    """TraceMap — crash to green."""

    TITLE = "TraceMap — crash to green"
    CSS = _CSS

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+d", "quit", "Quit", priority=True),
        Binding("t", "paste_trace", "Paste trace"),
        Binding("x", "toggle_inspector", "Inspector"),
        Binding("b", "blast_radius", "Blast radius"),
        Binding("f", "run_fix", "Run fix"),
        Binding("p", "show_proof", "Proof"),
        Binding("v", "open_editor", "Edit", show=False),
        Binding("enter", "open_editor", "Edit", show=False),
        Binding("question_mark", "help", "Help"),
    ]

    def __init__(self, crash_path: Path | None = None) -> None:
        """Initialise the app, optionally pre-loading *crash_path* on mount."""
        super().__init__()
        self._crash_path = crash_path
        self._repo_path: Path | None = None
        self._pack = None  # EvidencePack | None
        self._fix_result = None  # FixResult | None
        self._inspector_visible = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Build the three-column layout: pipeline rail, frames table, inspector."""
        pipeline_panel = Vertical(PipelineRail(id="pipeline"), id="pipeline-panel")
        pipeline_panel.border_title = r"\[f] Pipeline"

        trace_panel = Horizontal(
            Input(placeholder="Path to crash.txt …", id="trace-input"),
            id="trace-panel",
        )
        trace_panel.border_title = r"\[t] Traceback"

        frames_panel = Vertical(FramesTable(id="frames"), id="frames-panel")
        frames_panel.border_title = r"\[f] Frames"
        frames_panel.border_subtitle = "cursor · enter/v open in editor"

        details_scroll = VerticalScroll(
            Static("", id="inspector-details"),
            id="details-scroll",
        )
        details_scroll.can_focus = False

        inspector = Vertical(
            details_scroll,
            OptionList(id="relations"),
            id="inspector",
        )
        inspector.border_title = r"\[x] Inspector"
        inspector.border_subtitle = "blast-radius · callers/callees · tests"

        with Horizontal(id="body"):
            yield pipeline_panel
            with Vertical(id="main"):
                yield trace_panel
                yield frames_panel
                yield inspector
        yield Footer()

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Focus the frames table and auto-load crash_path when supplied."""
        # Focus the frames table so global keys (f/x/b/p) fire immediately.
        # The traceback input is driven via the `t` binding (TraceScreen modal)
        # and by typing a path and pressing Enter — it does not need startup focus.
        self.query_one("#frames", FramesTable).focus()
        if self._crash_path is not None and self._crash_path.exists():
            self.query_one("#trace-input", Input).value = str(self._crash_path)
            self._load_crash(self._crash_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_crash(self, crash_path: Path) -> None:
        """Index repo, build evidence, populate frames table."""
        from tracemap.evidence import build_evidence

        # Determine repo root
        repo = crash_path.parent
        for candidate in [crash_path.parent, *crash_path.parents]:
            if (candidate / "pyproject.toml").exists() or (candidate / "setup.py").exists():
                repo = candidate
                break
        self._repo_path = repo.resolve()

        pipeline = self.query_one("#pipeline", PipelineRail)
        pipeline.set_stage("Trace", "done", str(crash_path.name))
        pipeline.set_stage("Evidence", "running", "indexing…")

        def _worker() -> None:
            try:
                trace_text = crash_path.read_text(encoding="utf-8")
                pack = build_evidence(trace_text, repo)
                self._pack = pack
                self.call_from_thread(self._on_pack_ready, pack)
            except Exception as exc:  # noqa: BLE001
                self.call_from_thread(pipeline.set_stage, "Evidence", "failed", str(exc)[:60])

        threading.Thread(target=_worker, daemon=True).start()

    def _on_pack_ready(self, pack: object) -> None:
        """Called on main thread after evidence pack is built."""
        pipeline = self.query_one("#pipeline", PipelineRail)
        sym = getattr(pack, "failing_symbol", None)
        detail = sym.qualified_name if sym else "(not in index)"
        pipeline.set_stage("Evidence", "done", detail)

        table = self.query_one("#frames", FramesTable)
        table.load_pack(pack, repo=self._repo_path)  # type: ignore[arg-type]

        frames_panel = self.query_one("#frames-panel")
        frames_panel.border_subtitle = f"{len(pack.call_stack)} frames  ·  enter/v open in editor"  # type: ignore[union-attr]

    def _run_fix_worker(self) -> None:
        """Background thread: invoke engine and update pipeline."""
        from tracemap.engine import run_fix

        pipeline = self.query_one("#pipeline", PipelineRail)

        self.call_from_thread(pipeline.set_stage, "Bob", "running", "invoking tracemap-fixer…")

        try:
            result = run_fix(self._pack, self._repo_path)  # type: ignore[arg-type]
            self._fix_result = result

            if result.pending:
                self.call_from_thread(
                    pipeline.set_stage, "Bob", "done", "evidence pack written (pending)"
                )
                self.call_from_thread(pipeline.set_stage, "Patch", "pending", "")
                self.call_from_thread(pipeline.set_stage, "Verify", "pending", "")
            else:
                self.call_from_thread(pipeline.set_stage, "Bob", "done", "response received")
                self.call_from_thread(
                    pipeline.set_stage,
                    "Patch",
                    "done" if result.patch_diff else "failed",
                    result.rationale[:50] if result.rationale else "",
                )
                self.call_from_thread(pipeline.set_stage, "Verify", "running", "pytest…")
                self._run_verify_worker(result)

        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(pipeline.set_stage, "Bob", "failed", str(exc)[:60])

    def _run_verify_worker(self, result: object) -> None:
        """Run covering-test verification and update Verify stage."""
        from tracemap.verify import run_verify

        pipeline = self.query_one("#pipeline", PipelineRail)

        if self._pack is None or self._repo_path is None:
            self.call_from_thread(pipeline.set_stage, "Verify", "failed", "no pack")
            return

        test_paths = [sym.path for sym in self._pack.covering_tests]  # type: ignore[union-attr]
        if not test_paths:
            self.call_from_thread(pipeline.set_stage, "Verify", "done", "no covering tests")
            return

        try:
            verify = run_verify(self._repo_path, test_paths)
            if verify.ok:
                self.call_from_thread(
                    pipeline.set_stage,
                    "Verify",
                    "done",
                    f"{len(verify.passed_after)} passed",
                )
            else:
                self.call_from_thread(
                    pipeline.set_stage,
                    "Verify",
                    "failed",
                    f"regressions: {', '.join(verify.regression_introduced[:2])}",
                )
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(pipeline.set_stage, "Verify", "failed", str(exc)[:60])

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_paste_trace(self) -> None:
        """Open the trace-paste modal."""
        self.push_screen(TraceScreen(), self._on_trace_pasted)

    def _on_trace_pasted(self, text: str | None) -> None:
        if not text:
            return
        import os
        import tempfile

        fd, tmp_str = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        tmp = Path(tmp_str)
        tmp.write_text(text, encoding="utf-8")
        self.query_one("#trace-input", Input).value = str(tmp)
        self._load_crash(tmp)

    def action_toggle_inspector(self) -> None:
        """Show/hide the inspector panel."""
        self._inspector_visible = not self._inspector_visible
        inspector = self.query_one("#inspector")
        inspector.display = self._inspector_visible
        if self._inspector_visible and self._pack is not None:
            self._refresh_inspector()

    def _refresh_inspector(self) -> None:
        """Populate inspector with callers, callees, blast radius, tests."""
        if self._pack is None:
            return
        pack = self._pack
        sym = pack.failing_symbol

        lines: list[str] = []
        if sym:
            lines.append(f"[bold {TITLE}]{sym.qualified_name}[/]  [{MUTED}]{sym.kind}[/]\n")
            lines.append(f"[{INFO}]{sym.path}:{sym.line}[/]\n\n")
            lines.append(f"[{MUTED}]blast radius:[/] [{WARN}]{len(pack.blast_radius)} symbols[/]\n")
            lines.append(f"[{MUTED}]covering tests:[/] [{PASS}]{len(pack.covering_tests)}[/]\n")
        else:
            lines.append(f"[{MUTED}]crash frame not in index[/]\n")

        self.query_one("#inspector-details", Static).update("".join(lines))

        relations = self.query_one("#relations", OptionList)
        relations.clear_options()
        if sym:
            for caller in pack.callers:
                relations.add_option(f"← {caller.qualified_name}  [{caller.path}:{caller.line}]")
            for callee in pack.callees:
                relations.add_option(f"→ {callee.qualified_name}  [{callee.path}:{callee.line}]")
            for test_sym in pack.covering_tests:
                relations.add_option(f"🧪 {test_sym.qualified_name}")

    def action_blast_radius(self) -> None:
        """Populate inspector with the full blast-radius list."""
        if self._pack is None:
            self.notify("No evidence pack — load a trace first.", severity="warning")
            return
        if not self._inspector_visible:
            self.action_toggle_inspector()

        relations = self.query_one("#relations", OptionList)
        relations.clear_options()
        for sym, depth in self._pack.blast_radius:
            relations.add_option(f"[depth {depth}]  {sym.qualified_name}  {sym.path}:{sym.line}")

    def action_run_fix(self) -> None:
        """Invoke the Bob fix engine in a background thread."""
        if self._pack is None:
            self.notify("No evidence pack — load a trace first.", severity="warning")
            return
        pipeline = self.query_one("#pipeline", PipelineRail)
        pipeline.set_stage("Bob", "running", "invoking tracemap-fixer…")
        threading.Thread(target=self._run_fix_worker, daemon=True).start()

    def action_show_proof(self) -> None:
        """Open the ProofModal with the current fix result."""
        if self._fix_result is None:
            self.notify("No fix result — run `f` first.", severity="warning")
            return
        result = self._fix_result
        before = result.raw_response[:1000] if not result.pending else "(fix pending)"
        after = result.patch_diff or "(no patch)"
        self.push_screen(ProofModal(result.patch_diff, before, after))

    def action_open_editor(self) -> None:
        """Open the crash frame's file in $EDITOR."""
        if self._pack is None:
            return
        frame = self._pack.failing_frame
        editor = self._resolve_editor()
        path = Path(frame.path)
        if not path.is_absolute() and self._repo_path:
            path = self._repo_path / path
        if not path.exists():
            self.notify(f"File not found: {path}", severity="error")
            return
        cmd = [editor, f"+{frame.line}", str(path)]
        subprocess.Popen(cmd)

    @staticmethod
    def _resolve_editor() -> str:
        import os
        import shutil

        for env_var in ("VISUAL", "EDITOR"):
            val = os.environ.get(env_var, "")
            if val:
                return val
        for ed in ("code", "nano", "vim", "vi"):
            if shutil.which(ed):
                return ed
        return "vi"

    def action_help(self) -> None:
        """Show the help modal."""
        self.push_screen(HelpScreen())

    # ------------------------------------------------------------------
    # Input event: load crash file on Enter
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Load the crash file when the user presses Enter in the path input."""
        if event.input.id == "trace-input":
            path = Path(event.value.strip())
            if path.exists():
                self._load_crash(path)
            else:
                self.notify(f"File not found: {path}", severity="error")


# ---------------------------------------------------------------------------
# Standalone launcher
# ---------------------------------------------------------------------------


def main(crash_path: Path | None = None) -> None:
    """Launch the TraceMap TUI.

    Parameters
    ----------
    crash_path:
        Optional path to a ``crash.txt`` to pre-load on startup.
    """
    app = TraceMapApp(crash_path=crash_path)
    app.run()


if __name__ == "__main__":
    import sys

    _path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(_path)
