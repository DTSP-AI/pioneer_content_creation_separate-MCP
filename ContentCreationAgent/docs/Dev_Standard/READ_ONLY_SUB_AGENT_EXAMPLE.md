# SUB-AGENT TEMPLATE - LANGGRAPH NODE PATTERN
# ─────────────────────────────────────────────────────────────────────────────
# This is a project-agnostic template for building LangGraph sub-agent nodes
# that work within a multi-agent orchestration system.
#
# KEY PRINCIPLES:
# 1. State-Based Communication - All data passed via state objects, not memory
# 2. Single Responsibility - Each agent does ONE thing well
# 3. Async Execution - All nodes are async functions
# 4. Error Recovery - Use retry decorators and graceful failure handling
# 5. Tool Integration - Leverage LangChain tools for external APIs
# 6. Stateless Design - No persistent memory, state carries context
#
# USAGE:
# - Replace {{AGENT_NAME}} with your agent name (e.g., "data_processor")
# - Replace {{STATE_CLASS}} with your state schema class
# - Customize tool usage for your specific task
# - Adjust state updates to match your workflow
# ─────────────────────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: CORE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
# All imports for a typical LangGraph sub-agent node

from typing import Dict, Any, Optional, List
import logging
import asyncio

# State management (CUSTOMIZE: Import your project's state schema)
from backend.state.state_schema import (
    {{STATE_CLASS}},           # Replace with your state class (e.g., WorkflowState)
    update_workflow_phase,      # Optional: Phase tracking helper
    add_cost_to_workflow,       # Optional: Cost tracking helper
    update_workflow_stage       # Optional: Stage tracking helper
)

# Tool registry (CUSTOMIZE: Import your tool management system)
from backend.tools import ToolRegistry  # Or your tool management approach

# Error recovery patterns (RECOMMENDED: Use retry/timeout decorators)
from backend.graph.error_recovery import (
    with_retry,                 # Retry failed operations
    with_timeout,               # Timeout protection
    safe_node_execution,        # Top-level error wrapper
    STANDARD_RETRY,             # Standard retry config
    API_ERRORS                  # API error classification
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: MAIN NODE FUNCTION (CRITICAL PATTERN)
# ═══════════════════════════════════════════════════════════════════════════
# This is the core LangGraph node - async function that receives state and returns updates

@safe_node_execution  # Top-level error handler (optional but recommended)
async def {{AGENT_NAME}}_node(state: {{STATE_CLASS}}) -> Dict[str, Any]:
    """
    {{AGENT_NAME}} Node - Brief description of what this agent does.

    Architecture Compliance:
    - LangGraph node (async function)
    - Reads from {{STATE_CLASS}}
    - Returns state updates (Dict[str, Any])
    - Stateless execution (no persistent memory)

    Workflow:
    1. Extract inputs from state
    2. Validate prerequisites
    3. Execute core logic (use tools, call APIs, process data)
    4. Handle errors gracefully
    5. Return state updates

    Args:
        state: Current workflow state containing all context

    Returns:
        Dictionary of state updates to merge into workflow state

    Example State Updates:
        {
            "current_agent": "{{AGENT_NAME}}",
            "output_field": "result_value",
            "status": "completed",
            "metadata": {"info": "value"}
        }
    """
    try:
        logger.info("{{AGENT_NAME}} node started")

        # ───────────────────────────────────────────────────────────────────
        # STEP 1: Extract Inputs from State
        # ───────────────────────────────────────────────────────────────────
        # CUSTOMIZE: Extract the data your agent needs from state

        user_request = state.get("user_request", "")
        input_data = state.get("input_data")  # Replace with actual state field
        config = state.get("config", {})
        parsed_intent = state.get("parsed_intent", {})

        logger.info(f"Processing request: {user_request[:50]}...")

        # ───────────────────────────────────────────────────────────────────
        # STEP 2: Validate Prerequisites
        # ───────────────────────────────────────────────────────────────────
        # Ensure all required inputs are present

        if not input_data:
            raise ValueError("Missing required input_data in state")

        # Optional: Check for required configuration
        if not config.get("api_key"):
            logger.warning("API key not configured, using fallback mode")

        # ───────────────────────────────────────────────────────────────────
        # STEP 3: Load Tools (If Needed)
        # ───────────────────────────────────────────────────────────────────
        # CUSTOMIZE: Load tools specific to this agent's task

        tools = ToolRegistry.get_tools_for_agent("{{AGENT_NAME}}")

        # Example: Get specific tools by name
        primary_tool = ToolRegistry.get_tool_by_name("primary_tool_name")
        secondary_tool = ToolRegistry.get_tool_by_name("secondary_tool_name")

        if not primary_tool:
            raise RuntimeError("Primary tool not available")

        # ───────────────────────────────────────────────────────────────────
        # STEP 4: Execute Core Logic
        # ───────────────────────────────────────────────────────────────────
        # CUSTOMIZE: Implement your agent's main functionality

        # Example: Call a helper function with retry logic
        result = await _execute_primary_task(
            input_data=input_data,
            tool=primary_tool,
            config=config
        )

        # Example: Process the result
        processed_result = await _post_process_result(result)

        # Optional: Track costs (if applicable)
        cost = _calculate_operation_cost(result)

        logger.info(f"{{AGENT_NAME}} completed successfully: {processed_result[:100]}")

        # ───────────────────────────────────────────────────────────────────
        # STEP 5: Return State Updates
        # ───────────────────────────────────────────────────────────────────
        # Return dictionary with all state updates

        return {
            "current_agent": "{{AGENT_NAME}}",          # Track which agent just ran
            "output_field": processed_result,            # Main output (customize field name)
            "status": "success",                         # Status indicator
            "metadata": {                                # Additional metadata
                "agent": "{{AGENT_NAME}}",
                "operation_cost": cost,
                "timestamp": "2024-01-01T00:00:00Z"     # Add actual timestamp
            },
            # Optional: Update phase/stage tracking
            # "workflow_phase": update_workflow_phase(state, "completed"),
            # "total_cost_usd": add_cost_to_workflow(state, cost)
        }

    except ValueError as e:
        # Handle validation errors (missing inputs, invalid data)
        logger.error(f"Validation error in {{AGENT_NAME}}: {e}")
        return {
            "current_agent": "{{AGENT_NAME}}",
            "status": "failed",
            "error_message": f"Invalid input: {str(e)}",
            "error_type": "validation_error"
        }

    except RuntimeError as e:
        # Handle runtime errors (tool failures, external API errors)
        logger.error(f"Runtime error in {{AGENT_NAME}}: {e}")
        return {
            "current_agent": "{{AGENT_NAME}}",
            "status": "failed",
            "error_message": f"Execution failed: {str(e)}",
            "error_type": "runtime_error"
        }

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in {{AGENT_NAME}}: {e}", exc_info=True)
        return {
            "current_agent": "{{AGENT_NAME}}",
            "status": "failed",
            "error_message": f"Agent error: {str(e)}",
            "error_type": "unknown_error"
        }

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: HELPER FUNCTIONS (BUSINESS LOGIC)
# ═══════════════════════════════════════════════════════════════════════════
# Break down complex logic into focused helper functions

@with_retry(retries=STANDARD_RETRY, exceptions=API_ERRORS)  # Retry on API failures
async def _execute_primary_task(
    input_data: Any,
    tool: Any,
    config: Dict[str, Any]
) -> Any:
    """
    Execute the primary task with retry logic.

    CUSTOMIZE: Implement your core business logic here
    This function will automatically retry on API failures

    Args:
        input_data: Data to process
        tool: LangChain tool to use
        config: Configuration parameters

    Returns:
        Result from the tool execution

    Raises:
        RuntimeError: If task execution fails after retries
    """
    try:
        logger.info("Executing primary task...")

        # Example: Call LangChain tool
        if hasattr(tool, '_arun'):
            # Async tool execution
            result = await tool._arun(
                input=input_data,
                config=config.get("tool_config", {})
            )
        else:
            # Sync tool execution (wrap in async)
            result = await asyncio.to_thread(
                tool._run,
                input=input_data,
                config=config.get("tool_config", {})
            )

        return result

    except Exception as e:
        logger.error(f"Primary task failed: {e}")
        raise RuntimeError(f"Task execution failed: {str(e)}")


async def _post_process_result(result: Any) -> Any:
    """
    Post-process the raw result.

    CUSTOMIZE: Add your result transformation logic
    Examples:
    - Parse JSON responses
    - Format output for downstream agents
    - Validate result structure
    - Extract specific fields

    Args:
        result: Raw result from tool execution

    Returns:
        Processed result
    """
    try:
        # Example: Parse JSON if result is string
        if isinstance(result, str):
            import json
            try:
                parsed = json.loads(result)
                return parsed
            except json.JSONDecodeError:
                # Not JSON, return as-is
                return result

        return result

    except Exception as e:
        logger.warning(f"Post-processing failed: {e}, returning raw result")
        return result


def _calculate_operation_cost(result: Any) -> float:
    """
    Calculate cost of the operation.

    CUSTOMIZE: Implement your cost calculation logic
    Examples:
    - API call costs
    - Token usage costs
    - Processing time costs

    Args:
        result: Result from operation (may contain cost metadata)

    Returns:
        Cost in USD
    """
    # Example: Extract cost from result metadata
    if isinstance(result, dict):
        return result.get("cost_usd", 0.0)

    # Default: No cost tracking
    return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: VALIDATION HELPERS (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════
# Helper functions for input/output validation

def _validate_input(input_data: Any) -> bool:
    """
    Validate input data before processing.

    CUSTOMIZE: Add your validation rules
    Examples:
    - Type checking
    - Required field validation
    - Format validation
    - Range checking

    Args:
        input_data: Data to validate

    Returns:
        True if valid, False otherwise
    """
    if not input_data:
        return False

    # Example: Check for required fields if dict
    if isinstance(input_data, dict):
        required_fields = ["field1", "field2"]  # Customize
        return all(field in input_data for field in required_fields)

    return True


def _validate_output(output_data: Any) -> bool:
    """
    Validate output data before returning.

    CUSTOMIZE: Add your output validation rules

    Args:
        output_data: Data to validate

    Returns:
        True if valid, False otherwise
    """
    if not output_data:
        return False

    # Add custom validation logic
    return True

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: ALTERNATIVE PATTERNS (EXAMPLES)
# ═══════════════════════════════════════════════════════════════════════════
# Common sub-agent patterns for different use cases

# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 1: Simple Transformer Agent (No External Tools)
# ─────────────────────────────────────────────────────────────────────────────

async def transformer_node(state: {{STATE_CLASS}}) -> Dict[str, Any]:
    """
    Simple data transformation agent - no external tools needed.

    Use case: Format conversion, data cleaning, validation
    """
    try:
        input_data = state.get("raw_data")

        # Transform data
        transformed = {
            "formatted": input_data.upper(),  # Example transformation
            "validated": True
        }

        return {
            "current_agent": "transformer",
            "transformed_data": transformed
        }

    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        return {
            "current_agent": "transformer",
            "error_message": str(e)
        }


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 2: Parallel Processing Agent (Multiple Tool Calls)
# ─────────────────────────────────────────────────────────────────────────────

async def parallel_processor_node(state: {{STATE_CLASS}}) -> Dict[str, Any]:
    """
    Execute multiple operations in parallel for speed.

    Use case: API calls that don't depend on each other
    """
    try:
        tools = ToolRegistry.get_tools_for_agent("parallel_processor")

        # Execute multiple tools in parallel
        results = await asyncio.gather(
            tools[0]._arun(state.get("input1")),
            tools[1]._arun(state.get("input2")),
            tools[2]._arun(state.get("input3")),
            return_exceptions=True  # Don't fail if one task fails
        )

        # Process results
        successful_results = [r for r in results if not isinstance(r, Exception)]

        return {
            "current_agent": "parallel_processor",
            "results": successful_results,
            "total_processed": len(successful_results)
        }

    except Exception as e:
        logger.error(f"Parallel processing failed: {e}")
        return {"error_message": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 3: Decision Agent (Routing Logic)
# ─────────────────────────────────────────────────────────────────────────────

async def decision_node(state: {{STATE_CLASS}}) -> Dict[str, Any]:
    """
    Make routing decisions based on state.

    Use case: Conditional workflow routing, A/B testing, feature flags
    """
    try:
        criteria = state.get("decision_criteria", {})

        # Decision logic
        if criteria.get("type") == "premium":
            next_agent = "premium_processor"
            priority = "high"
        elif criteria.get("urgent"):
            next_agent = "fast_processor"
            priority = "urgent"
        else:
            next_agent = "standard_processor"
            priority = "normal"

        return {
            "current_agent": "decision",
            "next_agent": next_agent,
            "priority": priority,
            "routing_reason": f"Routed to {next_agent} based on criteria"
        }

    except Exception as e:
        logger.error(f"Decision failed: {e}")
        return {
            "next_agent": "default_processor",  # Fallback
            "error_message": str(e)
        }


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 4: Aggregator Agent (Collect Results from Multiple Agents)
# ─────────────────────────────────────────────────────────────────────────────

async def aggregator_node(state: {{STATE_CLASS}}) -> Dict[str, Any]:
    """
    Aggregate results from multiple upstream agents.

    Use case: Combine outputs, create summaries, merge data
    """
    try:
        # Collect results from previous agents
        agent1_result = state.get("agent1_output")
        agent2_result = state.get("agent2_output")
        agent3_result = state.get("agent3_output")

        # Aggregate
        combined_result = {
            "summary": "Combined results from 3 agents",
            "data": [agent1_result, agent2_result, agent3_result],
            "total_items": len([r for r in [agent1_result, agent2_result, agent3_result] if r])
        }

        return {
            "current_agent": "aggregator",
            "final_result": combined_result,
            "aggregation_complete": True
        }

    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        return {"error_message": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOMIZATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════
"""
To adapt this template to your sub-agent:

[ ] 1. Replace {{AGENT_NAME}} with your agent's name
[ ] 2. Replace {{STATE_CLASS}} with your state schema class
[ ] 3. Define what inputs your agent needs from state
[ ] 4. Determine what outputs your agent produces
[ ] 5. Choose or create tools your agent will use
[ ] 6. Implement core business logic in helper functions
[ ] 7. Add appropriate error handling for your use case
[ ] 8. Define state update fields your agent returns
[ ] 9. Add validation logic for inputs and outputs
[ ] 10. Configure retry/timeout decorators if needed
[ ] 11. Add cost tracking if applicable
[ ] 12. Write unit tests for your agent
[ ] 13. Document expected state structure
[ ] 14. Add logging for debugging
[ ] 15. Consider which pattern fits best (transformer, parallel, decision, aggregator)

STATE SCHEMA EXAMPLE:
from typing import TypedDict, Optional, List, Dict, Any

class WorkflowState(TypedDict, total=False):
    # Input fields
    user_request: str
    input_data: Any
    config: Dict[str, Any]
    parsed_intent: Dict[str, Any]

    # Agent tracking
    current_agent: str
    workflow_phase: str

    # Output fields
    output_field: Any
    status: str
    error_message: Optional[str]

    # Metadata
    metadata: Dict[str, Any]
    total_cost_usd: float

TOOL REGISTRY EXAMPLE:
class ToolRegistry:
    @staticmethod
    def get_tools_for_agent(agent_name: str) -> List[BaseTool]:
        # Return tools specific to this agent
        pass

    @staticmethod
    def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
        # Get specific tool by name
        pass

ERROR RECOVERY EXAMPLE:
from backend.graph.error_recovery import (
    with_retry,      # Decorator for retrying failed operations
    with_timeout,    # Decorator for timeout protection
    safe_node_execution  # Decorator for top-level error handling
)

STANDARD_RETRY = {"retries": 3, "delay": 1.0, "backoff": 2.0}
API_ERRORS = (ConnectionError, TimeoutError, Exception)

@with_retry(retries=STANDARD_RETRY, exceptions=API_ERRORS)
async def risky_operation():
    # This will retry up to 3 times with exponential backoff
    pass

LANGGRAPH INTEGRATION:
from langgraph.graph import StateGraph

# Create graph
workflow = StateGraph(WorkflowState)

# Add your agent as a node
workflow.add_node("{{AGENT_NAME}}", {{AGENT_NAME}}_node)

# Add edges (define flow)
workflow.add_edge("start", "{{AGENT_NAME}}")
workflow.add_edge("{{AGENT_NAME}}", "next_agent")

# Compile
app = workflow.compile()
"""

# ═══════════════════════════════════════════════════════════════════════════
# TESTING EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════
"""
Unit test example for your sub-agent:

import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_{{AGENT_NAME}}_success():
    # Arrange
    mock_state = {
        "user_request": "test request",
        "input_data": {"field1": "value1", "field2": "value2"},
        "config": {"api_key": "test_key"}
    }

    # Act
    result = await {{AGENT_NAME}}_node(mock_state)

    # Assert
    assert result["current_agent"] == "{{AGENT_NAME}}"
    assert result["status"] == "success"
    assert "output_field" in result

@pytest.mark.asyncio
async def test_{{AGENT_NAME}}_missing_input():
    # Arrange
    mock_state = {
        "user_request": "test request"
        # Missing input_data
    }

    # Act
    result = await {{AGENT_NAME}}_node(mock_state)

    # Assert
    assert result["status"] == "failed"
    assert "error_message" in result
    assert result["error_type"] == "validation_error"
"""
