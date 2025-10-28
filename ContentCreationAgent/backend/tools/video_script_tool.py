"""
Video Script Generator Tool

Generates engaging video scripts using Anthropic Claude.
Used by ContentCreationAgent for content creation.
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import logging
import openai

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoScriptInput(BaseModel):
    """Input schema for video script generation."""
    topic: str = Field(description="The main topic or trend for the video")
    platform: str = Field(
        default="tiktok",
        description="Target platform: 'tiktok' or 'youtube_shorts'"
    )
    duration_seconds: int = Field(
        default=30,
        description="Desired video duration in seconds (15-60)"
    )
    tone: str = Field(
        default="engaging",
        description="Tone: 'professional', 'casual', 'energetic', 'educational'"
    )


class VideoScriptGeneratorTool(BaseTool):
    """
    Generate video scripts using Claude API.

    Creates platform-optimized scripts for TikTok and YouTube Shorts.
    """

    name: str = "video_script_generator"
    description: str = """
    Generate an engaging video script for TikTok or YouTube Shorts.
    Provide a topic, target platform, duration, and tone.
    Returns a formatted script with hook, body, and call-to-action.
    """
    args_schema: Type[BaseModel] = VideoScriptInput

    def _run(
        self,
        topic: str,
        platform: str = "tiktok",
        duration_seconds: int = 30,
        tone: str = "engaging"
    ) -> str:
        """Sync execution (not used)."""
        import asyncio
        return asyncio.run(self._arun(topic, platform, duration_seconds, tone))

    async def _arun(
        self,
        topic: str,
        platform: str = "tiktok",
        duration_seconds: int = 30,
        tone: str = "engaging"
    ) -> str:
        """
        Async execution.

        Args:
            topic: Video topic
            platform: Target platform
            duration_seconds: Video length
            tone: Script tone

        Returns:
            JSON string with script and metadata
        """
        try:
            # Use Claude 3.5 Sonnet for creative script generation (better quality)
            # Fallback to OpenAI if Claude key not available
            use_anthropic = False
            if settings.ANTHROPIC_API_KEY:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                model = settings.ANTHROPIC_MODEL
                use_anthropic = True
                logger.info("Using Claude 3.5 Sonnet for script generation")
            elif settings.OPENAI_API_KEY:
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                model = settings.OPENAI_SCRIPT_MODEL
                use_anthropic = False
                logger.info("Using OpenAI GPT for script generation (fallback)")
            else:
                raise ValueError("Either ANTHROPIC_API_KEY or OPENAI_API_KEY is required for script generation")

            # Calculate word count (average speaking rate: 150 words/minute)
            target_word_count = int((duration_seconds / 60) * 150)

            # Build prompt
            prompt = self._build_script_prompt(
                topic, platform, duration_seconds, target_word_count, tone
            )

            # Call LLM API (Claude or OpenAI)
            if use_anthropic:
                response = await client.messages.create(
                    model=model,
                    max_tokens=1000,
                    temperature=0.7,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                script = response.content[0].text
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
            else:
                response = await client.chat.completions.create(
                    model=model,
                    max_tokens=1000,
                    temperature=0.7,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                script = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            # Calculate cost
            cost_usd = self._calculate_cost(input_tokens, output_tokens, use_anthropic)

            logger.info(
                f"Generated script for '{topic}' "
                f"({output_tokens} tokens, ${cost_usd:.4f})"
            )

            import json
            return json.dumps({
                "status": "success",
                "script": script,
                "word_count": len(script.split()),
                "platform": platform,
                "duration_seconds": duration_seconds,
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens
                },
                "cost_usd": cost_usd,
                "service_name": model  # Track which service/model was actually used
            }, indent=2)

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            import json
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _build_script_prompt(
        self,
        topic: str,
        platform: str,
        duration_seconds: int,
        target_word_count: int,
        tone: str
    ) -> str:
        """Build Claude prompt for script generation."""

        platform_guidelines = {
            "tiktok": "TikTok format: Start with a hook, deliver value quickly, end with CTA",
            "youtube_shorts": "YouTube Shorts: Grab attention early, provide clear value, encourage likes/subscribes"
        }

        return f"""You are an expert short-form video script writer.

Task: Write a {duration_seconds}-second video script for {platform.upper()}.

Topic: {topic}
Target Word Count: {target_word_count} words
Tone: {tone}
Platform Guidelines: {platform_guidelines.get(platform, '')}

Script Structure:
1. HOOK (0-3 seconds): Grab attention immediately
2. BODY ({duration_seconds-6} seconds): Deliver value, tell story, share insight
3. CTA (last 3 seconds): Clear call-to-action

Requirements:
- Write in spoken language (conversational, not formal)
- Use short sentences for easy reading
- Include pauses where natural
- Optimize for voiceover delivery
- Stay within word count

Format the output as:

[HOOK]
<hook text>

[BODY]
<body text>

[CTA]
<cta text>

Begin writing the script now:"""

    def _calculate_cost(self, input_tokens: int, output_tokens: int, use_anthropic: bool = True) -> float:
        """Calculate API cost based on token usage using centralized calculator."""
        from backend.utils.cost_calculator import calculate_llm_cost

        # Determine model name
        if use_anthropic:
            model = settings.ANTHROPIC_MODEL or "claude-3-5-sonnet"
        else:
            model = "gpt-5-nano"  # Using gpt-5-nano for all text content

        return calculate_llm_cost(input_tokens, output_tokens, model)
