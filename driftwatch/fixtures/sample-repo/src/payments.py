"""PayFlux integration. Endpoint shapes come from the public API reference —
which can change without an API version bump."""

from __future__ import annotations

import requests

BASE = "https://api.payflux.example"


def create_charge(amount_cents: int, source_token: str) -> dict:
    response = requests.post(
        f"{BASE}/v2/charges",
        json={"amount": amount_cents, "currency": "usd", "source": source_token},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def refund(charge_id: str) -> dict:
    response = requests.post(f"{BASE}/v2/refunds", json={"charge_id": charge_id}, timeout=10)
    response.raise_for_status()
    return response.json()


def legacy_tokenize(card: dict) -> str:
    # NOTE: still on the old tokens endpoint — migration long overdue.
    response = requests.post(f"{BASE}/v1/tokens", json={"card": card}, timeout=10)
    response.raise_for_status()
    return response.json()["token"]
