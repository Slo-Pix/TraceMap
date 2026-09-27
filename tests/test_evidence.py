"""Unit tests for tracemap.evidence against examples/buggy_app.

Run from the tracemap/ directory:

    pytest tests/test_evidence.py -v

The tests use the REAL traceback in examples/buggy_app/crash.txt so that the
acceptance criterion "the pack correctly identifies the failing function from
crash.txt" is verified by the test suite itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tracemap.evidence import EvidencePack, build_evidence, render_markdown

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent / "examples" / "buggy_app"
CRASH_TXT = REPO_ROOT.parent.parent / "examples" / "buggy_app" / "crash.txt"

# Re-resolve relative to *this* file so the test works regardless of cwd.
_HERE = Path(__file__).resolve().parent
_TRACEMAP_ROOT = _HERE.parent          # tracemap/
_BUGGY_APP = _TRACEMAP_ROOT / "examples" / "buggy_app"
_CRASH_TXT = _BUGGY_APP / "crash.txt"


@pytest.fixture(scope="module")
def crash_text() -> str:
    return _CRASH_TXT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pack(crash_text: str) -> EvidencePack:
    return build_evidence(crash_text, _BUGGY_APP)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEvidencePackStructure:
    """The pack is correctly shaped and frozen."""

    def test_is_frozen(self, pack: EvidencePack) -> None:
        with pytest.raises((AttributeError, TypeError)):
            pack.failing_frame = None  # type: ignore[misc]

    def test_has_failing_frame(self, pack: EvidencePack) -> None:
        assert pack.failing_frame is not None

    def test_has_call_stack_list(self, pack: EvidencePack) -> None:
        assert isinstance(pack.call_stack, list)
        assert len(pack.call_stack) > 0

    def test_crash_frame_is_first_in_call_stack(self, pack: EvidencePack) -> None:
        """Index 0 of call_stack must be the crash site (innermost frame)."""
        first_frame, _ = pack.call_stack[0]
        assert first_frame is pack.failing_frame

    def test_callers_is_list_of_symbols(self, pack: EvidencePack) -> None:
        from codemap.model import Symbol

        assert isinstance(pack.callers, list)
        for sym in pack.callers:
            assert isinstance(sym, Symbol)


class TestFailingSymbolIdentification:
    """The pack must name the correct failing function from crash.txt.

    crash.txt shows the ZeroDivisionError in ``divide_total`` inside
    ``examples/buggy_app/report.py`` at line 10.
    """

    def test_failing_symbol_is_not_none(self, pack: EvidencePack) -> None:
        """divide_total is in the index — symbol must not be None."""
        assert pack.failing_symbol is not None, (
            "Expected failing_symbol to be 'divide_total' but got None. "
            "Check that the buggy_app repo is indexed correctly."
        )

    def test_failing_symbol_name(self, pack: EvidencePack) -> None:
        """The identified symbol must be divide_total."""
        assert pack.failing_symbol is not None
        assert pack.failing_symbol.name == "divide_total", (
            f"Expected 'divide_total', got '{pack.failing_symbol.name}'"
        )

    def test_failing_frame_name(self, pack: EvidencePack) -> None:
        """The failing frame's function name must also be divide_total."""
        assert pack.failing_frame.name == "divide_total"

    def test_failing_frame_file_is_report(self, pack: EvidencePack) -> None:
        assert "report.py" in pack.failing_frame.path


class TestBlastRadius:
    """The blast radius must be non-empty: divide_total IS called by others."""

    def test_blast_radius_non_empty(self, pack: EvidencePack) -> None:
        assert len(pack.blast_radius) > 0, (
            "blast_radius is empty — divide_total should be called by "
            "average_per_category and overall_average at minimum."
        )

    def test_blast_radius_contains_depth_one(self, pack: EvidencePack) -> None:
        depths = {depth for _, depth in pack.blast_radius}
        assert 1 in depths, "Expected at least one depth-1 direct caller."

    def test_blast_radius_tuples(self, pack: EvidencePack) -> None:
        for item in pack.blast_radius:
            sid, depth = item
            assert isinstance(sid, str)
            assert isinstance(depth, int)
            assert depth >= 1


class TestSource:
    """source must be the real function body text, not the signature string."""

    def test_source_contains_return_statement(self, pack: EvidencePack) -> None:
        assert "return total / count" in pack.source, (
            f"Expected 'return total / count' in source, got:\n{pack.source!r}"
        )

    def test_source_is_multiline(self, pack: EvidencePack) -> None:
        assert "\n" in pack.source

    def test_source_starts_with_def(self, pack: EvidencePack) -> None:
        assert pack.source.lstrip().startswith("def divide_total")


class TestCallers:
    """callers must be the two direct callers from index.incoming, not traceback frames."""

    def test_callers_names(self, pack: EvidencePack) -> None:
        names = {sym.name for sym in pack.callers}
        assert names == {"average_per_category", "overall_average"}, (
            f"Expected {{average_per_category, overall_average}}, got {names}"
        )

    def test_callers_count(self, pack: EvidencePack) -> None:
        assert len(pack.callers) == 2


class TestCallees:
    """divide_total has no callees (leaf function)."""

    def test_callees_is_list(self, pack: EvidencePack) -> None:
        assert isinstance(pack.callees, list)


class TestCoveringTests:
    """Covering tests list is well-formed (may be empty for this fixture)."""

    def test_covering_tests_is_list(self, pack: EvidencePack) -> None:
        assert isinstance(pack.covering_tests, list)

    def test_covering_tests_are_symbols(self, pack: EvidencePack) -> None:
        from codemap.model import Symbol

        for sym in pack.covering_tests:
            assert isinstance(sym, Symbol)
            assert sym.name.lower().startswith("test")


class TestUnmappedFrames:
    """Frozen / built-in frames (runpy) should be unmapped; report.py frames mapped."""

    def test_unmapped_frames_is_list(self, pack: EvidencePack) -> None:
        assert isinstance(pack.unmapped_frames, list)

    def test_report_frames_are_mapped(self, pack: EvidencePack) -> None:
        """All frames from report.py should be in the index."""
        unmapped_paths = {f.path for f in pack.unmapped_frames}
        for path in unmapped_paths:
            assert "report.py" not in path, (
                f"Frame in report.py was unmapped: {path}"
            )


class TestRenderMarkdown:
    """render_markdown produces a non-empty string with expected sections."""

    def test_returns_string(self, pack: EvidencePack) -> None:
        md = render_markdown(pack)
        assert isinstance(md, str)
        assert len(md) > 0

    def test_contains_failing_symbol_name(self, pack: EvidencePack) -> None:
        md = render_markdown(pack)
        assert "divide_total" in md

    def test_contains_section_headers(self, pack: EvidencePack) -> None:
        md = render_markdown(pack)
        assert "## TraceMap Evidence Pack" in md
        assert "Failing Frame" in md
        assert "Blast Radius" in md

    def test_source_block_in_markdown(self, pack: EvidencePack) -> None:
        md = render_markdown(pack)
        assert "```python" in md
        assert "return total / count" in md, (
            "render_markdown must emit the actual source body, not just a signature"
        )

    def test_direct_callers_in_markdown(self, pack: EvidencePack) -> None:
        md = render_markdown(pack)
        assert "average_per_category" in md
        assert "overall_average" in md
