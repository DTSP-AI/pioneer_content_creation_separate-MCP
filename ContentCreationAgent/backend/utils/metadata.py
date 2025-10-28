"""
Metadata formatting utilities for content platforms.

Provides consistent metadata generation (captions, titles, descriptions, hashtags)
across TikTok, YouTube Shorts, and other platforms.
"""

from typing import Dict, Any, List, Tuple
from backend.utils.topic_mappings import (
    get_tags_for_topic,
    get_emoji_for_topic,
    TIKTOK_TOPIC_TAGS
)


def format_tiktok_metadata(
    script: str,
    trend_topic: str,
    parsed_intent: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """
    Format caption and hashtags for TikTok.

    TikTok best practices:
    - Caption: 150-300 characters (max 2200)
    - Hashtags: 3-5 relevant tags
    - Include trending tags
    - Call-to-action

    Args:
        script: Video script
        trend_topic: Trending topic
        parsed_intent: Parsed user intent

    Returns:
        Tuple of (caption, hashtags)
    """
    # Extract first sentence or first 200 chars for caption
    caption_text = script.split('.')[0] if '.' in script else script[:200]

    # Add call-to-action
    caption_text += "\n\n👉 Follow for more!"

    # Generate hashtags
    hashtags = []

    # Add topic-based tags
    topic = parsed_intent.get("topic", "General")
    hashtags.extend(get_tags_for_topic(topic, platform="tiktok", limit=2))

    # Add platform tags
    hashtags.extend(["tiktok", "viral", "fyp"])

    # Add trend-related tag (if applicable)
    if trend_topic and len(trend_topic.split()) <= 2:
        trend_tag = trend_topic.lower().replace(" ", "")
        if len(trend_tag) < 20:
            hashtags.append(trend_tag)

    # Limit to 5 hashtags
    hashtags = hashtags[:5]

    # Ensure caption isn't too long
    if len(caption_text) > 300:
        caption_text = caption_text[:297] + "..."

    return caption_text, hashtags


def format_youtube_metadata(
    script: str,
    trend_topic: str,
    parsed_intent: Dict[str, Any]
) -> Tuple[str, str, List[str]]:
    """
    Generate title, description, and tags for YouTube Shorts.

    YouTube best practices:
    - Title: 60-70 characters (max 100)
    - Description: 200-300 characters (max 5000)
    - Tags: 5-8 relevant tags
    - Include #Shorts

    Args:
        script: Video script
        trend_topic: Trending topic
        parsed_intent: Parsed user intent

    Returns:
        Tuple of (title, description, tags)
    """
    # Generate title
    if trend_topic:
        title = trend_topic
    else:
        # Use first sentence of script
        title = script.split('.')[0] if '.' in script else script[:60]

    # Add emoji based on topic
    topic = parsed_intent.get("topic", "General")
    emoji = get_emoji_for_topic(topic)
    title = f"{emoji} {title}"

    # Truncate title if too long
    if len(title) > 70:
        title = title[:67] + "..."

    # Generate description
    # First paragraph of script
    description_text = script.split('\n\n')[0] if '\n\n' in script else script[:300]

    # Add call-to-action and #Shorts
    description_text += "\n\n👍 Like and Subscribe for more!\n\n#Shorts"

    # Add topic tags to description
    description_tags = get_tags_for_topic(topic, platform="youtube", limit=3)
    description_text += " " + " ".join([f"#{tag}" for tag in description_tags])

    # Truncate description if too long
    if len(description_text) > 400:
        description_text = description_text[:397] + "..."

    # Generate tags (YouTube tags, not hashtags)
    tags = []

    # Add topic-based tags
    tags.extend(get_tags_for_topic(topic, platform="youtube", limit=3))

    # Add platform tags
    tags.extend(["Shorts", "Short Video", "YouTube Shorts"])

    # Add trend tag
    if trend_topic:
        tags.append(trend_topic)

    # Limit to 8 tags
    tags = tags[:8]

    return title, description_text, tags
