"""Tests for the expense report."""

from __future__ import annotations

from examples.buggy_app.report import average_per_category, overall_average, summarize_expenses

POPULATED = [
    {"category": "travel", "amount": 100.0, "owner": "ana"},
    {"category": "travel", "amount": 300.0, "owner": "raj"},
    {"category": "meals", "amount": 50.0, "owner": "ana"},
    {"category": "hardware", "amount": 900.0, "owner": "sam"},
    {"category": "training", "amount": 250.0, "owner": "ana"},
]


def test_average_per_category():
    assert average_per_category(POPULATED[:2]) == 200.0


def test_overall_average():
    assert overall_average(POPULATED) == 320.0


def test_summarize_every_category_present():
    averages = summarize_expenses(POPULATED)
    assert averages["travel"] == 200.0
    assert averages["hardware"] == 900.0


def test_average_per_category_empty_entries_returns_zero():
    """average_per_category([]) must return 0.0, not raise ZeroDivisionError.

    Regression for: ZeroDivisionError in divide_total when a category has no
    expense records (e.g. 'training' in the real dataset).
    Fix site: average_per_category — guard added before calling divide_total.
    """
    assert average_per_category([]) == 0.0
