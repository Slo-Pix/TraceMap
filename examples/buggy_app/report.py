"""Summarise expenses into a per-category report."""

from __future__ import annotations

from examples.buggy_app.loader import CATEGORIES, entries_for


def divide_total(total: float, count: int) -> float:
    """Average of `total` spread over `count` entries."""
    return total / count


def average_per_category(entries: list[dict[str, object]]) -> float:
    """Mean amount across one category's entries."""
    total = sum(float(entry["amount"]) for entry in entries)
    return divide_total(total, len(entries))


def overall_average(expenses: list[dict[str, object]]) -> float:
    """Mean amount across every expense, ignoring category."""
    total = sum(float(expense["amount"]) for expense in expenses)
    return divide_total(total, len(expenses))


def summarize_expenses(expenses: list[dict[str, object]]) -> dict[str, float]:
    """Average spend for every known category."""
    return {
        category: average_per_category(entries_for(expenses, category))
        for category in CATEGORIES
    }


def build_report(expenses: list[dict[str, object]]) -> str:
    """Render the period summary as text."""
    averages = summarize_expenses(expenses)
    lines = [f"{category:<10} {amount:>9.2f}" for category, amount in averages.items()]
    lines.append(f"{'ALL':<10} {overall_average(expenses):>9.2f}")
    return "\n".join(lines)
