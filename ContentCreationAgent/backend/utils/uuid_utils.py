"""
UUID Validation Utilities

Provides safe UUID parsing with consistent error handling across the application.
Prevents crashes from invalid workflow IDs like "demo" or malformed strings.
"""

import uuid
from fastapi import HTTPException
from typing import Union


def safe_uuid(input_id: str, prefix: str = "wf-", param_name: str = "workflow_id") -> uuid.UUID:
    """
    Safely convert a string ID to UUID with consistent error handling.

    Handles:
    - IDs with prefix (e.g., "wf-4f3c65e9-8fd6-4fcd-8dc8-8e6224f8f0c2")
    - Raw UUIDs (e.g., "4f3c65e9-8fd6-4fcd-8dc8-8e6224f8f0c2")
    - Invalid formats like "demo" or empty strings

    Args:
        input_id: String ID to convert
        prefix: Expected prefix to strip (default: "wf-")
        param_name: Parameter name for error message

    Returns:
        UUID object

    Raises:
        HTTPException: If ID format is invalid (status_code=400)
    """
    if not input_id or not isinstance(input_id, str):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name}: must be a non-empty string"
        )

    # Strip prefix if present
    id_without_prefix = input_id
    if input_id.startswith(prefix):
        id_without_prefix = input_id[len(prefix):]

    # Attempt UUID conversion
    try:
        return uuid.UUID(id_without_prefix)
    except (ValueError, AttributeError, TypeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format: '{input_id}' (expected UUID)"
        )


def validate_workflow_id(workflow_id: str) -> uuid.UUID:
    """
    Validate workflow ID is a proper UUID.

    Args:
        workflow_id: Workflow identifier string

    Returns:
        UUID object

    Raises:
        HTTPException: If workflow_id is invalid
    """
    return safe_uuid(workflow_id, prefix="wf-", param_name="workflow_id")

