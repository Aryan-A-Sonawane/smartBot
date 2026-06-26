"""Cost estimation (before run) and actuals (after run) for the cost panel."""

from __future__ import annotations

from ..config import price_for
from ..schemas import CostInfo
from ..utils import estimate_tokens

# Overhead tokens for system prompts + tool instructions across a request.
_SYSTEM_OVERHEAD = 400


def estimate_cost(
    combined_context: str, model: str, expected_output_tokens: int = 350
) -> CostInfo:
    """Predict cost from the input size before any LLM call is made."""
    input_tokens = estimate_tokens(combined_context) + _SYSTEM_OVERHEAD
    price = price_for(model)
    usd = (input_tokens * price["in"] + expected_output_tokens * price["out"]) / 1_000_000
    return CostInfo(
        model=model,
        input_tokens=input_tokens,
        output_tokens=expected_output_tokens,
        estimated_usd=round(usd, 6),
    )


def actual_cost(input_tokens: int, output_tokens: int, model: str) -> CostInfo:
    """Compute the real cost from accumulated token usage after the run."""
    price = price_for(model)
    usd = (input_tokens * price["in"] + output_tokens * price["out"]) / 1_000_000
    return CostInfo(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        actual_usd=round(usd, 6),
    )
