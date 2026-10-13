"""The error every output check raises, carrying the layer so the retry prompt can name it."""

from __future__ import annotations


class OutputError(ValueError):
    """A model answer that failed one validation layer: schema, fields or citations."""

    def __init__(self, layer: str, message: str) -> None:
        super().__init__(f"{layer}: {message}")
        self.layer = layer
        self.message = message
