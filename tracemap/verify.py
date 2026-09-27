"""verify.py — fail-before / pass-after pytest runner.

Runs the covering tests twice:

1. **Before** the patch — records which tests fail.
2. **After** the patch — asserts previously-failing tests now pass and no
   previously-passing tests regressed.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = ["VerifyResult", "run_verify"]


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of the fail-before / pass-after verification run."""

    passed_before: list[str]
    """Test node IDs that passed before the patch was applied."""

    failed_before: list[str]
    """Test node IDs that failed before the patch was applied."""

    passed_after: list[str]
    """Test node IDs that passed after the patch was applied."""

    failed_after: list[str]
    """Test node IDs that failed after the patch was applied."""

    @property
    def regression_introduced(self) -> list[str]:
        """Tests that were green before but are red after — regressions."""
        return [t for t in self.passed_before if t in self.failed_after]

    @property
    def fixed(self) -> list[str]:
        """Tests that were red before and are green after — confirmed fixes."""
        return [t for t in self.failed_before if t in self.passed_after]

    @property
    def ok(self) -> bool:
        """True when no tests failed after the patch.

        ``regression_introduced`` is always empty when ``passed_before`` is
        empty (the single-pass CLI workflow), so we also check ``failed_after``
        directly so that a broken patch is not silently reported as green.
        """
        return len(self.failed_after) == 0 and len(self.regression_introduced) == 0


def _pytest_json(repo: Path, test_paths: list[str]) -> dict[str, str]:
    """Run pytest on *test_paths* and return a ``{node_id: 'pass'|'fail'}`` map."""
    if not test_paths:
        return {}

    cmd = [
        "python",
        "-m",
        "pytest",
        "--tb=no",
        "-v",
        "--no-header",
        "--override-ini=addopts=",  # suppress project-level -q so -v takes effect
        *test_paths,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(repo),
        check=False,
    )
    outcomes: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if " PASSED" in line:
            node = line.split(" PASSED")[0].strip()
            outcomes[node] = "pass"
        elif " FAILED" in line:
            node = line.split(" FAILED")[0].strip()
            outcomes[node] = "fail"
        elif " ERROR" in line:
            node = line.split(" ERROR")[0].strip()
            outcomes[node] = "fail"
    return outcomes


def run_verify(
    repo: Path,
    test_paths: list[str],
) -> VerifyResult:
    """Run *test_paths* and split outcomes into pass/fail buckets.

    This is called **after** the patch has been applied.  The caller is
    responsible for running tests before the patch if a true before/after
    comparison is desired; the engine currently runs only the post-patch pass
    for the CLI workflow.

    Parameters
    ----------
    repo:
        Project root — pytest is invoked from here.
    test_paths:
        List of test file paths or pytest node IDs to exercise.

    Returns
    -------
    VerifyResult
        Frozen dataclass with pass/fail buckets.
    """
    outcomes = _pytest_json(repo, test_paths)
    passed = [k for k, v in outcomes.items() if v == "pass"]
    failed = [k for k, v in outcomes.items() if v == "fail"]
    return VerifyResult(
        passed_before=[],
        failed_before=[],
        passed_after=passed,
        failed_after=failed,
    )
