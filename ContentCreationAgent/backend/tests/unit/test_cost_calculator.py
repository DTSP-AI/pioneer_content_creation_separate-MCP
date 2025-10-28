"""
Unit Tests for Cost Calculator

Tests the centralized cost calculation utility.
"""

import pytest
from backend.utils.cost_calculator import (
    calculate_llm_cost,
    calculate_tts_cost,
    calculate_video_generation_cost
)


class TestLLMCostCalculation:
    """Test LLM API cost calculations."""

    def test_calculate_claude_sonnet_cost(self):
        """Test Claude 3.5 Sonnet cost calculation."""
        cost = calculate_llm_cost(
            input_tokens=1000,
            output_tokens=500,
            model="claude-3-5-sonnet"
        )

        # Expected: (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
        assert cost == pytest.approx(0.0105)

    def test_calculate_gpt4_turbo_cost(self):
        """Test GPT-4 Turbo cost calculation."""
        cost = calculate_llm_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4-turbo"
        )

        # Expected: (1000/1000 * 0.01) + (500/1000 * 0.03) = 0.01 + 0.015 = 0.025
        assert cost == pytest.approx(0.025)

    def test_calculate_gpt5_nano_cost(self):
        """Test GPT-5 Nano cost calculation (lowest tier)."""
        cost = calculate_llm_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-5-nano"
        )

        # Expected: (1000/1000 * 0.0005) + (500/1000 * 0.0015) = 0.0005 + 0.00075 = 0.00125
        assert cost == pytest.approx(0.00125)

    def test_unknown_model_uses_fallback(self):
        """Test that unknown models use GPT-4 Turbo as fallback."""
        cost = calculate_llm_cost(
            input_tokens=1000,
            output_tokens=500,
            model="unknown-model"
        )

        # Should fallback to gpt-4-turbo pricing
        assert cost == pytest.approx(0.025)


class TestTTSCostCalculation:
    """Test TTS cost calculations."""

    def test_calculate_tts_cost(self):
        """Test TTS cost per character."""
        cost = calculate_tts_cost(character_count=1000)

        # Expected: 1000 * 0.00003 = 0.03
        assert cost == pytest.approx(0.03)

    def test_calculate_empty_tts_cost(self):
        """Test TTS cost for empty string."""
        cost = calculate_tts_cost(character_count=0)

        # Expected: 0
        assert cost == 0.0

    def test_calculate_large_tts_cost(self):
        """Test TTS cost for large text."""
        cost = calculate_tts_cost(character_count=10000)

        # Expected: 10000 * 0.00003 = 0.3
        assert cost == pytest.approx(0.3)


class TestVideoGenerationCost:
    """Test video generation cost calculations."""

    def test_calculate_creatomate_cost(self):
        """Test Creatomate video generation cost."""
        cost = calculate_video_generation_cost(
            service="creatomate",
            duration_seconds=60
        )

        # Expected: 0.05 USD per video
        assert cost == pytest.approx(0.05)

    def test_calculate_piapi_cost(self):
        """Test PiAPI video generation cost."""
        cost = calculate_video_generation_cost(
            service="piapi",
            duration_seconds=120
        )

        # Expected: 0.10 USD per video
        assert cost == pytest.approx(0.10)

    def test_unknown_service_raises_error(self):
        """Test that unknown service raises ValueError."""
        with pytest.raises(ValueError, match="Unknown video generation service"):
            calculate_video_generation_cost(
                service="unknown-service",
                duration_seconds=60
            )


class TestCostCalculationIntegration:
    """Integration tests for cost calculation."""

    def test_total_video_workflow_cost(self):
        """Test cost calculation for complete video workflow."""
        # Script generation (Claude)
        script_cost = calculate_llm_cost(
            input_tokens=500,
            output_tokens=300,
            model="claude-3-5-sonnet"
        )

        # TTS generation
        tts_cost = calculate_tts_cost(character_count=500)

        # Video generation
        video_cost = calculate_video_generation_cost(
            service="piapi",
            duration_seconds=30
        )

        total_cost = script_cost + tts_cost + video_cost

        assert total_cost > 0
        assert script_cost > 0
        assert tts_cost > 0
        assert video_cost > 0

