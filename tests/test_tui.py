"""Headless Textual pilot tests for TraceMapApp.

Verifies:
  1. On mount, ``app.focused`` is the FramesTable (not the Input), so global
     key bindings like ``f``, ``x``, ``b``, ``p`` fire rather than typing.
  2. Pressing ``f`` with no evidence pack loaded does NOT type "f" into the Input.
  3. ``_rel_path`` helper in FramesTable correctly shortens absolute paths.
"""

from __future__ import annotations

import asyncio

from tracemap.widgets.frames import _rel_path

# ---------------------------------------------------------------------------
# Unit tests for path helper — no Textual runtime needed
# ---------------------------------------------------------------------------


def test_rel_path_shortens(tmp_path):
    """Absolute path under repo root is made relative."""
    src = str(tmp_path / "examples" / "buggy_app" / "report.py")
    assert _rel_path(src, tmp_path) == "examples/buggy_app/report.py"


def test_rel_path_outside_repo(tmp_path):
    """Path outside the repo root is returned unchanged."""
    other = "/usr/lib/python3/dist-packages/foo.py"
    assert _rel_path(other, tmp_path) == other


def test_rel_path_no_repo():
    """When repo is None the raw path is returned unchanged."""
    raw = "/some/absolute/path.py"
    assert _rel_path(raw, None) == raw


# ---------------------------------------------------------------------------
# Textual pilot tests — driven via asyncio.run so no pytest-asyncio needed
# ---------------------------------------------------------------------------


def _run_pilot(coro):
    """Run a coroutine that uses app.run_test() in a clean event loop."""
    return asyncio.run(coro)


def test_focused_widget_is_frames_table_on_mount():
    """After mounting, FramesTable holds focus — not the Input."""
    from tracemap.tui import TraceMapApp
    from tracemap.widgets.frames import FramesTable

    async def _run():
        app = TraceMapApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app.focused, FramesTable), (
                f"Expected FramesTable to hold focus on mount, got {type(app.focused).__name__}"
            )

    _run_pilot(_run())


def test_f_key_triggers_run_fix_not_input():
    """Pressing 'f' calls action_run_fix (notifies) rather than typing into Input."""
    from textual.widgets import Input

    from tracemap.tui import TraceMapApp

    async def _run():
        app = TraceMapApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Confirm focus is NOT on the Input
            assert not isinstance(app.focused, Input), (
                "Input must not hold focus at startup — it would swallow 'f'"
            )
            # Press 'f': with no pack loaded, action_run_fix posts a notification.
            # It must not raise and must not type 'f' into the Input.
            await pilot.press("f")
            await pilot.pause()
            trace_input = app.query_one("#trace-input", Input)
            assert trace_input.value == "", (
                f"Input value should be empty after pressing 'f'; got {trace_input.value!r}"
            )

    _run_pilot(_run())
