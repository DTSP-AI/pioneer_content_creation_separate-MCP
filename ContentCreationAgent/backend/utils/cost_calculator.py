"""
Cost Calculation Utilities

Centralized source of truth for all cost calculations in the system.
Prevents inconsistency and duplication across agents and tools.

Usage:
    from backend.utils.cost_calculator import calculate_llm_cost, calculate_tts_cost

    cost = calculate_llm_cost(input_tokens, output_tokens, model="claude-3-5-sonnet")
    tts_cost = calculate_tts_cost(character_count)
"""

import logging
from typing import Literal

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# LLM Pricing (per 1K tokens)
COST_PER_1K_TOKENS = {
    # OpenAI GPT models (for all text content)
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    "gpt-5-nano": {"input": 0.0005, "output": 0.0015},
    # Anthropic Claude models (legacy, kept for compatibility)
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
}

# TTS Pricing (per character)
COST_PER_CHARACTER_TTS = 0.00003  # ElevenLabs pricing

# Video Generation Pricing
COST_PER_VIDEO_RENDER = 0.05  # Creatomate estimate
COST_PER_PIAPI_VIDEO = 0.10  # PiAPI.ai estimate (varies by model)


def calculate_llm_cost(
    input_tokens: int,
    output_tokens: int,
    model: str
) -> float:
    """
    Calculate LLM API cost based on token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name (e.g., "claude-3-5-sonnet", "gpt-4-turbo")

    Returns:
        Cost in USD

    Raises:
        ValueError: If model pricing not found
    """
    costs = COST_PER_1K_TOKENS.get(model)

    if not costs:
        logger.warning(
            f"Unknown model pricing for '{model}', using gpt-5-nano as fallback"
        )
        costs = COST_PER_1K_TOKENS["gpt-5-nano"]

    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]

    total_cost = input_cost + output_cost

    logger.debug(
        f"Cost calculation for {model}: "
        f"{input_tokens} input + {output_tokens} output = ${total_cost:.6f}"
    )

    return total_cost


def calculate_tts_cost(character_count: int) -> float:
    """
    Calculate TTS (Text-to-Speech) cost.

    Args:
        character_count: Number of characters to convert to speech

    Returns:
        Cost in USD
    """
    return character_count * COST_PER_CHARACTER_TTS


def calculate_video_generation_cost(
    service: Literal["creatomate", "piapi"],
    duration_seconds: int = 60
) -> float:
    """
    Calculate video generation cost.

    Args:
        service: Service provider ("creatomate" or "piapi")
        duration_seconds: Video duration in seconds

    Returns:
        Cost in USD
    """
    if service == "creatomate":
        return COST_PER_VIDEO_RENDER
    elif service == "piapi":
        return COST_PER_PIAPI_VIDEO
    else:
        raise ValueError(f"Unknown video generation service: {service}")


def record_cost_ledger(
    session: "AsyncSession",
    tenant_id: str,
    workflow_id: str,
    service: str,
    cost_usd: float,
    metadata: dict = None
) -> None:
    """
    Record cost in the database ledger.

    Args:
        session: Database session
        tenant_id: Tenant UUID
        workflow_id: Workflow UUID
        service: Service name (e.g., "llm", "tts", "video")
        cost_usd: Cost in USD
        metadata: Additional metadata
    """
    from backend.database.models import CostLedger, uuid

    cost_entry = CostLedger(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        service=service,
        amount_usd=cost_usd,
        metadata=metadata or {}
    )

    session.add(cost_entry)

    logger.info(
        f"Cost ledger entry: {service} = ${cost_usd:.6f} for workflow {workflow_id}"
    )

