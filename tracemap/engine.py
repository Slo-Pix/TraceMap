"""Fix engine: invoke IBM Bob with the tracemap-fixer Skill and return a FixResult.

Two implementations are selected at runtime:

- ``_invoke_bob_shell``     – ``bob -p "<instruction>"`` capturing stdout.
                              Used when ``bob`` is on PATH.
- ``_invoke_file_handoff``  – writes ``.tracemap/pack.md`` with the evidence pack
                              plus a ready-to-paste instruction, prints the path, and
                              returns a FixResult marked pending.
                              Used when ``bob`` is absent.

``invoke_bob(pack_path, mode)`` picks the right implementation via
``shutil.which("bob")``.  Everything downstream is identical either way.
"""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from tracemap.evidence import EvidencePack, render_markdown

__all__ = ["FixResult", "invoke_bob", "run_fix"]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

_PENDING_SENTINEL = "PENDING"


@dataclass(frozen=True)
class FixResult:
    """Result returned by the fix engine after one Bob invocation.

    When Bob could not be invoked headlessly, ``pending`` is ``True``
    and the other text fields are empty strings — the CLI must say so
    honestly rather than fabricate a result.
    """

    patch_diff: str
    """Unified diff of the applied patch, or '' when pending."""

    test_path: str
    """Path (or pytest node-ID) of the new regression test, or '' when pending."""

    rationale: str
    """One-sentence root-cause explanation from Bob, or '' when pending."""

    raw_response: str
    """Full text returned by Bob (stdout), or '' when pending."""

    pending: bool = False
    """True when the evidence pack was written but Bob has not been invoked yet."""

    pack_path: str = ""
    """Absolute path to the written evidence pack (set whether pending or not)."""


# ---------------------------------------------------------------------------
# Bob invocation helpers
# ---------------------------------------------------------------------------

_INSTRUCTION = textwrap.dedent(
    """\
    You are running in tracemap-fixer mode.
    The file attached as context is a TraceMap evidence pack.
    Follow the tracemap-fixer Skill instructions to produce a minimal root-cause
    patch and a regression test that FAILS before and PASSES after the fix.
    Then verify with pytest and report the summary block.
    """
).strip()


def _write_pack(pack_path: Path, pack_md: str) -> None:
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack_md, encoding="utf-8")


def _invoke_bob_shell(pack_path: Path, mode: str, raw_md: str) -> FixResult:
    """Run ``bob -p "<instruction>" --chat-mode=<mode> …`` and capture stdout."""
    _write_pack(pack_path, raw_md)

    instruction = f"{_INSTRUCTION}\n\nEvidence pack: {pack_path}"
    cmd = [
        "bob",
        "-p",
        instruction,
        f"--chat-mode={mode}",
        "--yolo",
        "--hide-intermediary-output",
        "--add-file",
        str(pack_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr

    return FixResult(
        patch_diff=_extract_section(output, "PATCH:"),
        test_path=_extract_section(output, "REGRESSION:"),
        rationale=_extract_section(output, "ROOT CAUSE:"),
        raw_response=output,
        pending=False,
        pack_path=str(pack_path),
    )


def _extract_section(text: str, label: str) -> str:
    """Pull the value after a ``LABEL:   value`` line from Bob's summary block."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith(label.upper()):
            _, _, value = stripped.partition(":")
            return value.strip()
    return ""


def _invoke_file_handoff(pack_path: Path, mode: str, raw_md: str) -> FixResult:
    """Write the evidence pack and a ready-to-paste instruction; return pending."""
    instruction_path = pack_path.with_suffix(".instruction.txt")

    ready_to_paste = (
        "# TraceMap fix — ready-to-paste Bob instruction\n"
        "#\n"
        "# bob is not on PATH; run the command below manually once bob is installed.\n"
        "# --------------------------------------------------------------------\n\n"
        f'bobide chat -m {mode} --add-file "{pack_path}" "{_INSTRUCTION}"\n'
    )

    _write_pack(pack_path, raw_md)
    instruction_path.write_text(ready_to_paste, encoding="utf-8")

    print(f"[tracemap] Evidence pack written → {pack_path}")
    print(f"[tracemap] Paste instruction   → {instruction_path}")

    return FixResult(
        patch_diff="",
        test_path="",
        rationale="",
        raw_response=_PENDING_SENTINEL,
        pending=True,
        pack_path=str(pack_path),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def invoke_bob(pack_path: Path, mode: str, raw_md: str) -> FixResult:
    """Dispatch to the correct Bob implementation based on availability.

    Parameters
    ----------
    pack_path:
        Where the evidence pack should be written (e.g. ``.tracemap/pack.md``).
    mode:
        Bob chat-mode name (e.g. ``"tracemap-fixer"``).
    raw_md:
        Rendered Markdown of the evidence pack.
    """
    if shutil.which("bob") is not None:
        return _invoke_bob_shell(pack_path, mode, raw_md)
    return _invoke_file_handoff(pack_path, mode, raw_md)


def run_fix(pack: EvidencePack, repo: Path) -> FixResult:
    """Invoke Bob non-interactively with the tracemap-fixer Skill.

    Parameters
    ----------
    pack:
        Evidence pack built by :func:`tracemap.evidence.build_evidence`.
    repo:
        Root of the project being fixed (used to locate the pack drop directory).

    Returns
    -------
    FixResult
        Frozen dataclass with the patch, regression test path, and rationale.
        When Bob cannot be invoked headlessly, ``FixResult.pending`` is ``True``.
    """
    pack_md = render_markdown(pack)
    pack_path = repo / ".tracemap" / "pack.md"
    return invoke_bob(pack_path, "tracemap-fixer", pack_md)
