"""Load expense records for a reporting period."""

from __future__ import annotations

CATEGORIES = ("travel", "meals", "hardware", "training")


def load_expenses() -> list[dict[str, object]]:
    """Return the current period's expense records."""
    return [
        {"category": "travel", "amount": 320.0, "owner": "ana"},
        {"category": "travel", "amount": 180.0, "owner": "raj"},
        {"category": "meals", "amount": 42.5, "owner": "ana"},
        {"category": "hardware", "amount": 1299.0, "owner": "sam"},
        # note: nobody filed a "training" expense this period
    ]


def entries_for(expenses: list[dict[str, object]], category: str) -> list[dict[str, object]]:
    """Every expense filed under one category."""
    return [expense for expense in expenses if expense["category"] == category]
