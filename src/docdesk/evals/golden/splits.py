"""The planned dev and test split for the whole golden set, fixed before any item is written."""

from __future__ import annotations

# How many items of each type the finished set has (docs/modules/evals.md), 100 in all.
TYPE_COUNTS = {
    "single_fact": 31,
    "multi_chunk": 19,
    "structured": 19,
    "mixed": 6,
    "unanswerable": 19,
    "adversarial": 6,
}
# How many of each type are held out as test, 40 in all. 40 percent of each type, rounded so the
# total is exactly 40 (the types with the biggest remainders, multi chunk, structured and
# unanswerable, round up).
TEST_COUNTS = {
    "single_fact": 12,
    "multi_chunk": 8,
    "structured": 8,
    "mixed": 2,
    "unanswerable": 8,
    "adversarial": 2,
}


def tests_before(kind: str, position: int) -> int:
    """How many test items fall among the first `position` items of a type, spread evenly."""
    count, tests = TYPE_COUNTS[kind], TEST_COUNTS[kind]
    return (2 * position * tests + count) // (2 * count)


def split_for(kind: str, position: int) -> str:
    """Give the item at this 0-based position of its type a split, so any batch is balanced too."""
    if kind not in TYPE_COUNTS:
        raise ValueError(f"unknown item type {kind!r}")
    if not 0 <= position < TYPE_COUNTS[kind]:
        raise ValueError(f"the plan has {TYPE_COUNTS[kind]} {kind} items, not position {position}")
    return "test" if tests_before(kind, position + 1) > tests_before(kind, position) else "dev"
