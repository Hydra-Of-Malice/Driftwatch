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
    """The Bright Data API/CLI returned an error envelope.

    `category` places the failure in the taxonomy below so callers (and the UI)
    can tell a vendor refusal apart from a genuine scraper failure. `hint` is the
    operator-facing next step. Neither ever carries credentials.
    """

    code = "brightdata_error"

    def __init__(self, message: str, *, category: str | None = None, hint: str = "",
                 status: int | None = None, operation: str = "", **context: object) -> None:
        super().__init__(message, **context)
        self.status = status
        self.operation = operation
        if category is None:
            category, auto_hint = classify_vendor_error(message, status)
            hint = hint or auto_hint
        self.category = category
        self.hint = hint

    def to_dict(self) -> dict:
        """Structured form for the audit ledger and the API surface."""
        return {
            "code": self.code, "category": self.category, "operation": self.operation,
            "status": self.status, "message": str(self), "hint": self.hint,
            **{k: v for k, v in self.context.items()},
        }


class ConfigError(DriftwatchError):
    """Invalid or missing configuration (e.g. live mode without an API key)."""

    code = "config_error"


# -- vendor failure taxonomy ------------------------------------------------------
# Distinguishes "Bright Data refused/could not serve us" from "our scraper broke" and
# from "our own code is wrong". Without this the UI would report a vendor 403 as a
# scraper failure — see docs/LIVE_VALIDATION.md for the real envelopes behind each.


class FailureCategory:
    """Stable, machine-readable failure categories (logged + surfaced in the UI)."""

    AUTHENTICATION = "VENDOR_AUTH_ERROR"          # 401 — key missing/invalid/revoked
    VENDOR_PERMISSION = "VENDOR_PERMISSION_ERROR"  # 403 — key valid, action not permitted
    ACCOUNT_PLAN = "VENDOR_ACCOUNT_ERROR"          # 402/plan/credit refusals
    VENDOR_RATE_LIMIT = "VENDOR_RATE_LIMIT"        # 429 — AI-Flow concurrent-job cap
    VENDOR_UNAVAILABLE = "VENDOR_UNAVAILABLE"      # 5xx — feature disabled / outage
    VENDOR_TIMEOUT = "VENDOR_TIMEOUT"              # CLI exceeded our wall clock
    VENDOR_BAD_RESPONSE = "VENDOR_BAD_RESPONSE"    # non-JSON / unparseable envelope
    CLI_COMPATIBILITY = "CLI_COMPATIBILITY"        # CLI missing, or envelope shape drifted
    NETWORK = "NETWORK_ERROR"
    SCRAPER_FAILURE = "SCRAPER_FAILURE"            # the scraper ran and genuinely failed
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    SEMANTIC_DRIFT = "SEMANTIC_DRIFT"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    APPLICATION_ERROR = "APPLICATION_ERROR"


# Vendor error strings observed live (Aug 2026), mapped to a category + operator hint.
# First match wins; matched case-insensitively against the vendor's message body.
VENDOR_ERROR_SIGNATURES: list[tuple[str, str, str]] = [
    ("automation not allowed", FailureCategory.VENDOR_PERMISSION,
     "Scraper Studio AI Flow (POST /dca/collectors/<id>/automate_template) is refused for this "
     "ACCOUNT. Verified 2026-08-23 by controlled experiment: an Admin-permission API token lifts "
     "the 403 on /customer/balance but NOT on automate_template, so this is an account-level "
     "feature entitlement, not token scope. Re-issuing the token will not help; the collector is "
     "still created and usable, only the AI generation step is withheld."),
    ("self healing tool is temporarily disabled", FailureCategory.VENDOR_UNAVAILABLE,
     "Bright Data has disabled the self-healing endpoint service-side (HTTP 503). This is not an "
     "account or credential problem and cannot be fixed client-side; retry when it is re-enabled."),
    ("lacks the required permissions", FailureCategory.VENDOR_PERMISSION,
     "API token is under-scoped for this endpoint. Re-issue it with the required permissions."),
    ("collector does not have a template", FailureCategory.CLI_COMPATIBILITY,
     "The collector exists but its template is still a stub — AI generation never completed. "
     "This is the downstream symptom of a blocked `automate_template` trigger."),
    ("automation not found", FailureCategory.VENDOR_PERMISSION,
     "No automation job to resume — the heal that would have created it never started."),
    ("cannot run more than", FailureCategory.VENDOR_RATE_LIMIT,
     "AI-Flow concurrent-job cap hit; serialise `scraper create` calls or wait for the backoff."),
    ("unauthorized", FailureCategory.AUTHENTICATION, "BRIGHTDATA_API_KEY is missing or invalid."),
    ("invalid api key", FailureCategory.AUTHENTICATION, "BRIGHTDATA_API_KEY is missing or invalid."),
]


def classify_vendor_error(message: str, status: int | None = None) -> tuple[str, str]:
    """Map a vendor message (+ optional HTTP status) to (category, operator hint).

    Message signatures win over the status code: Bright Data returns 403 for both
    "token under-scoped" and "feature not enabled for you", and the body is what
    tells them apart.
    """
    text = (message or "").lower()
    for needle, category, hint in VENDOR_ERROR_SIGNATURES:
        if needle in text:
            return category, hint
    if status == 401:
        return FailureCategory.AUTHENTICATION, "BRIGHTDATA_API_KEY is missing or invalid."
    if status == 402:
        return FailureCategory.ACCOUNT_PLAN, "Account/plan or credit limit refused this action."
    if status == 403:
        return FailureCategory.VENDOR_PERMISSION, ("Action not permitted for this token/account. "
                                                   "Check BOTH token permissions and account "
                                                   "feature entitlements — they fail identically.")
    if status == 429:
        return FailureCategory.VENDOR_RATE_LIMIT, "Rate limited by Bright Data; back off and retry."
    if status is not None and status >= 500:
        return FailureCategory.VENDOR_UNAVAILABLE, "Bright Data server-side failure; retry later."
    return FailureCategory.APPLICATION_ERROR, ""
