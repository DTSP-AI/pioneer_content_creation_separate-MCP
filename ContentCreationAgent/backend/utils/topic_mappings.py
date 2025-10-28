"""
Shared topic-to-tags and emoji mappings for content platforms.

Provides consistent tag and emoji mappings across TikTok, YouTube Shorts,
and other content platforms.
"""

from typing import Dict, List


# Topic-based hashtag mappings for TikTok (lowercase)
TIKTOK_TOPIC_TAGS: Dict[str, List[str]] = {
    "AI and Technology": ["ai", "tech", "technology", "innovation"],
    "Business and Entrepreneurship": ["business", "entrepreneur", "startup", "success"],
    "Health and Fitness": ["fitness", "health", "workout", "wellness"],
    "Food and Cooking": ["food", "cooking", "recipe", "foodie"],
    "Travel": ["travel", "adventure", "explore", "wanderlust"],
    "General": ["trending", "viral", "fyp"]
}

# Topic-based tags for YouTube (Title Case)
YOUTUBE_TOPIC_TAGS: Dict[str, List[str]] = {
    "AI and Technology": ["AI", "Technology", "Tech", "Innovation"],
    "Business and Entrepreneurship": ["Business", "Entrepreneur", "Startup", "Success"],
    "Health and Fitness": ["Fitness", "Health", "Workout", "Wellness"],
    "Food and Cooking": ["Food", "Cooking", "Recipe", "Foodie"],
    "Travel": ["Travel", "Adventure", "Explore", "Wanderlust"],
    "General": ["Trending", "Viral", "Shorts"]
}

# Topic-to-emoji mappings
TOPIC_EMOJI_MAP: Dict[str, str] = {
    "AI and Technology": "🤖",
    "Business and Entrepreneurship": "💼",
    "Health and Fitness": "💪",
    "Food and Cooking": "🍳",
    "Travel": "✈️",
    "General": "✨"
}


def get_tags_for_topic(topic: str, platform: str = "tiktok", limit: int = None) -> List[str]:
    """
    Get tags for a given topic and platform.

    Args:
        topic: Topic name (e.g., "AI and Technology")
        platform: Platform name ("tiktok" or "youtube")
        limit: Optional limit on number of tags to return

    Returns:
        List of tags for the topic
    """
    if platform.lower() == "tiktok":
        tags = TIKTOK_TOPIC_TAGS.get(topic, ["trending"])
    elif platform.lower() == "youtube":
        tags = YOUTUBE_TOPIC_TAGS.get(topic, ["Trending"])
    else:
        tags = TIKTOK_TOPIC_TAGS.get(topic, ["trending"])

    return tags[:limit] if limit else tags


def get_emoji_for_topic(topic: str) -> str:
    """
    Get emoji for a given topic.

    Args:
        topic: Topic name (e.g., "AI and Technology")

    Returns:
        Emoji string for the topic
    """
    return TOPIC_EMOJI_MAP.get(topic, "✨")
