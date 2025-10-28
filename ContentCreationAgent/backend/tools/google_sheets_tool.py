"""
Google Sheets Trends Tool

Fetches trending topics from a Google Sheets spreadsheet.
Used by ContentCreationAgent to identify viral content opportunities.
"""

from typing import Optional, Type, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import logging

import gspread
from google.oauth2.service_account import Credentials

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleSheetsTrendsInput(BaseModel):
    """Input schema for Google Sheets trends tool."""
    category: Optional[str] = Field(
        default=None,
        description="Optional category filter (e.g., 'tech', 'lifestyle', 'business')"
    )
    limit: int = Field(
        default=10,
        description="Maximum number of trends to return"
    )


class GoogleSheetsTrendsTool(BaseTool):
    """
    Fetch trending topics from Google Sheets.

    This tool connects to a Google Sheets spreadsheet containing
    trending topics, hashtags, and metadata for content creation.

    Expected Sheet Format:
        Column A: Topic
        Column B: Category
        Column C: Engagement Score
        Column D: Trending Since
        Column E: Notes
    """

    name: str = "google_sheets_trends"
    description: str = """
    Fetch trending topics from Google Sheets for content inspiration.
    Use this to discover viral trends, popular hashtags, and content ideas.
    Returns a list of trending topics with metadata.
    """
    args_schema: Type[BaseModel] = GoogleSheetsTrendsInput

    def _run(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Synchronous execution (not used in async workflows).
        """
        return self._execute(category, limit)

    async def _arun(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Async execution.

        Args:
            category: Optional category filter
            limit: Max number of trends

        Returns:
            JSON string with trend data
        """
        return self._execute(category, limit)

    def _execute(
        self,
        category: Optional[str],
        limit: int
    ) -> str:
        """
        Execute Google Sheets query.

        Returns:
            JSON-formatted string with trends
        """
        try:
            # Check if credentials are configured
            if not settings.GOOGLE_SHEETS_CREDENTIALS_PATH:
                logger.warning("Google Sheets credentials not configured")
                return self._get_mock_trends(category, limit)

            # Authenticate with Google Sheets
            creds = Credentials.from_service_account_file(
                settings.GOOGLE_SHEETS_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            client = gspread.authorize(creds)

            # Open spreadsheet
            sheet = client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
            worksheet = sheet.sheet1  # or sheet.worksheet("Trends")

            # Fetch data
            records = worksheet.get_all_records()

            # Filter by category if specified
            if category:
                records = [r for r in records if r.get("Category", "").lower() == category.lower()]

            # Sort by engagement score (if available)
            records.sort(key=lambda x: x.get("Engagement Score", 0), reverse=True)

            # Limit results
            records = records[:limit]

            # Format output
            trends = []
            for record in records:
                trends.append({
                    "topic": record.get("Topic", ""),
                    "category": record.get("Category", ""),
                    "engagement_score": record.get("Engagement Score", 0),
                    "trending_since": record.get("Trending Since", ""),
                    "notes": record.get("Notes", "")
                })

            logger.info(f"Fetched {len(trends)} trends from Google Sheets")

            import json
            return json.dumps({
                "status": "success",
                "count": len(trends),
                "trends": trends
            }, indent=2)

        except Exception as e:
            logger.error(f"Google Sheets fetch failed: {e}")
            return json.dumps({
                "status": "error",
                "message": str(e),
                "trends": []
            })

    def _get_mock_trends(self, category: Optional[str], limit: int) -> str:
        """
        Return mock trends when Google Sheets is not configured.

        Used for development/testing.
        """
        import json

        mock_trends = [
            {
                "topic": "AI-powered content creation",
                "category": "tech",
                "engagement_score": 95,
                "trending_since": "2025-01-10",
                "notes": "High engagement on TikTok and YouTube"
            },
            {
                "topic": "Short-form video strategies",
                "category": "marketing",
                "engagement_score": 88,
                "trending_since": "2025-01-12",
                "notes": "Trending across all platforms"
            },
            {
                "topic": "Sustainable living tips",
                "category": "lifestyle",
                "engagement_score": 82,
                "trending_since": "2025-01-08",
                "notes": "Growing audience interest"
            },
            {
                "topic": "Remote work productivity hacks",
                "category": "business",
                "engagement_score": 79,
                "trending_since": "2025-01-11",
                "notes": "Consistent performer"
            },
            {
                "topic": "Budget travel destinations",
                "category": "travel",
                "engagement_score": 75,
                "trending_since": "2025-01-09",
                "notes": "Seasonal spike"
            }
        ]

        # Filter by category
        if category:
            mock_trends = [t for t in mock_trends if t["category"].lower() == category.lower()]

        # Limit
        mock_trends = mock_trends[:limit]

        logger.info(f"Returning {len(mock_trends)} mock trends (Google Sheets not configured)")

        return json.dumps({
            "status": "success",
            "source": "mock_data",
            "count": len(mock_trends),
            "trends": mock_trends
        }, indent=2)
