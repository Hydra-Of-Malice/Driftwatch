"""Budget guard — burns in pricing assumptions that live on a web page.

These constants were copied from NimbusAI's pricing page. Nothing tells this
file when that page changes; Driftwatch does.
"""

PRICE_ASSUMPTIONS_PER_1M = {
    "nimbus-large-2": {"input": 2.50, "output": 10.00},  # copied 2026-07-02
    "nimbus-mini-3": {"input": 0.15, "output": 0.60},
}

MONTHLY_BUDGET_USD = 4000


def projected_cost(input_m: float, output_m: float, model: str = "nimbus-large-2") -> float:
    prices = PRICE_ASSUMPTIONS_PER_1M[model]
    return input_m * prices["input"] + output_m * prices["output"]
