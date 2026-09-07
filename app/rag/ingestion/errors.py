"""Ingestion-specific errors."""


class ParsingError(Exception):
    """A permanent, user-explainable parsing failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
