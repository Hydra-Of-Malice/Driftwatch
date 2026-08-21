"""Typed error taxonomy.

Every failure mode the pipeline can hit maps to one of these classes, and every
one of them maps to a visible pipeline state — no silent log-line failures.
"""

from __future__ import annotations


class DriftwatchError(Exception):
    """Base class. `code` is stable and machine-readable; it lands in the audit ledger."""

    code = "driftwatch_error"

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.context = context


class FetchError(DriftwatchError):
    """The target page could not be fetched (dead, blocked, relocated)."""

    code = "fetch_error"

    def __init__(self, message: str, status: int | None = None, **context: object) -> None:
        super().__init__(message, **context)
        self.status = status


class ContractViolation(DriftwatchError):
    """Extraction landed but failed the source's contract (schema/invariants/semantics)."""

    code = "contract_violation"


class HealRejected(DriftwatchError):
    """A proposed heal failed verification and was rejected."""

    code = "heal_rejected"


class BudgetExceeded(DriftwatchError):
    """Bright Data credit budget guard tripped."""

    code = "budget_exceeded"


class BrightDataError(DriftwatchError):
    """The Bright Data API/CLI returned an error envelope."""

    code = "brightdata_error"


class ConfigError(DriftwatchError):
    """Invalid or missing configuration (e.g. live mode without an API key)."""

    code = "config_error"
