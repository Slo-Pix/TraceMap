"""Entry point: print this period's expense report."""

from __future__ import annotations

from examples.buggy_app.loader import load_expenses
from examples.buggy_app.report import build_report


def main() -> None:
    print(build_report(load_expenses()))


if __name__ == "__main__":
    main()
