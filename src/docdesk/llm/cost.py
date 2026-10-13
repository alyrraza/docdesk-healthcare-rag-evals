"""Price table and cost computation (AC-OBS-03); prices are list prices in USD per 1M tokens."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Bump this date when any price changes, so old traces can be re-costed against the right table.
PRICE_TABLE_VERSION = "2026-10-13"
PER_MILLION = Decimal(1_000_000)


class UnknownModelError(KeyError):
    """A model with no price entry; failing is safer than reporting a paid call as free."""


@dataclass(frozen=True)
class Price:
    """USD per one million input and output tokens."""

    input_per_m: Decimal
    output_per_m: Decimal


PRICES: dict[str, Price] = {
    "openai/gpt-oss-120b": Price(Decimal("0.15"), Decimal("0.60")),
    "qwen/qwen3.8-27b": Price(Decimal("0.80"), Decimal("4.00")),
}
FREE = Price(Decimal("0"), Decimal("0"))


def compute_cost(model: str, tokens_in: int, tokens_out: int) -> Decimal:
    """Work out the dollar cost of one call, so cost per query is code and not a guess."""
    price = FREE if model.endswith(":free") else PRICES.get(model)
    if price is None:
        raise UnknownModelError(f"no price listed for model '{model}'")
    return (tokens_in * price.input_per_m + tokens_out * price.output_per_m) / PER_MILLION
