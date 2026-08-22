"""acme-support-bot: the demo codebase Driftwatch's Impact Graph scans.

A small but realistic integration: it calls NimbusAI for completions and
PayFlux for billing. When a watched page changes, Driftwatch maps the change
to these exact call sites.
"""

from __future__ import annotations

import os

from nimbus_sdk import NimbusClient  # type: ignore[import-not-found]

PRIMARY_MODEL = "nimbus-large-2"
VISION_MODEL = "nimbus-vision-1"

client = NimbusClient(api_key=os.environ["NIMBUS_API_KEY"])


def answer_ticket(ticket_text: str) -> str:
    response = client.complete(
        model="nimbus-large-2",
        max_tokens=800,
        prompt=f"Answer this support ticket helpfully:\n\n{ticket_text}",
    )
    return response.text


def analyze_screenshot(image_url: str) -> str:
    response = client.complete(model=VISION_MODEL, prompt="Describe the issue", image=image_url)
    return response.text
