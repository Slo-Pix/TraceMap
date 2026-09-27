"""PipelineRail — left-rail widget showing TraceMap's 5 pipeline stages."""

from __future__ import annotations

__all__ = ["PipelineRail"]

from dataclasses import dataclass
from typing import Literal

from rich.text import Text
from textual.widget import Widget

from tracemap.theme import (
    ACCENT,
    FAIL,
    GLYPH_DONE,
    GLYPH_FAILED,
    GLYPH_PENDING,
    GLYPH_RUNNING,
    MUTED,
    PASS,
    TITLE,
)

Status = Literal["pending", "running", "done", "failed"]

_STAGES: list[str] = ["Trace", "Evidence", "Bob", "Patch", "Verify"]

_GLYPH_MAP: dict[str, tuple[str, str]] = {
    "pending": GLYPH_PENDING,
    "running": GLYPH_RUNNING,
    "done": GLYPH_DONE,
    "failed": GLYPH_FAILED,
}

_NAME_COLOUR: dict[str, str] = {
    "pending": MUTED,
    "running": ACCENT,
    "done": PASS,
    "failed": FAIL,
}


@dataclass
class _StageState:
    name: str
    status: Status = "pending"
    detail: str = ""


class PipelineRail(Widget):
    """Left-rail widget (width 36) displaying the 5 TraceMap pipeline stages.

    Each stage shows a status glyph, stage name, and optional one-line detail.
    Call :meth:`set_stage` from any thread to drive live updates.
    """

    DEFAULT_CSS = """
    PipelineRail {
        width: 36;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._states: list[_StageState] = [_StageState(name=s) for s in _STAGES]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_stage(self, name: str, status: str, detail: str = "") -> None:
        """Drive a stage update from the app (thread-safe).

        Parameters
        ----------
        name   : one of "Trace", "Evidence", "Bob", "Patch", "Verify"
        status : one of "pending", "running", "done", "failed"
        detail : one-line detail text shown below the stage name (may be "")
        """
        for state in self._states:
            if state.name == name:
                state.status = status  # type: ignore[assignment]
                state.detail = detail
                break
        self.refresh()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> Text:
        """Return a :class:`rich.text.Text` renderable for all pipeline stages."""
        out = Text()

        # Header
        out.append("Pipeline\n", style=f"bold {TITLE}")
        out.append("\n")

        for i, state in enumerate(self._states):
            glyph, glyph_colour = _GLYPH_MAP.get(state.status, GLYPH_PENDING)
            name_colour = _NAME_COLOUR.get(state.status, MUTED)

            # Glyph + stage name on the same line
            out.append(f"  {glyph}  ", style=glyph_colour)
            out.append(f"{state.name}\n", style=name_colour)

            # Optional detail line, indented to align under the stage name
            if state.detail:
                out.append(f"     {state.detail}\n", style=MUTED)
            else:
                out.append("\n")

            # Blank separator between stages (but not after the last one)
            if i < len(self._states) - 1:
                out.append("\n")

        return out
