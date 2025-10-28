"""
Workflow Execution Engine

Handles background workflow execution, state management, and progress tracking.
Separated from routes.py to avoid circular imports.

CRITICAL: This module is the SINGLE point of workflow execution for the entire system.
It ensures LangGraph does ALL orchestration - no custom loops, no manual routing.

Architecture:
- LangGraph handles: supervisor → content_creation → [tiktok, youtube_shorts]
- This module handles: WebSocket broadcasting, database checkpoints, progress messages
- Zero custom orchestration logic - pure LangGraph delegation
"""

import logging
import uuid
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.graph import stream_workflow, create_checkpointer
from backend.database.models import WorkflowExecution
from backend.database.connection import open_session

# Import websocket_manager directly to avoid circular import through backend.api
import backend.api.websocket_manager as ws_module
ws_manager = ws_module.ws_manager
workflow_started_message = ws_module.workflow_started_message
node_completed_message = ws_module.node_completed_message
workflow_completed_message = ws_module.workflow_completed_message
workflow_error_message = ws_module.workflow_error_message

logger = logging.getLogger(__name__)


async def resume_workflow_after_review(workflow_id: str, review_id: str):
    """
    Resume workflow execution after review approval.

    When review_gate_node calls interrupt(), the graph pauses and the original
    execution stops. To resume, we must invoke the graph again with the same
    config. LangGraph will detect the interrupt and continue from there.

    Args:
        workflow_id: Workflow ID to resume
        review_id: Review ID that was approved
    """
    from backend.graph import build_content_workflow, create_checkpointer

    logger.info(f"Resuming workflow {workflow_id} after review approval: {review_id}")

    try:
        # Build graph with checkpointer (same as original execution)
        checkpointer = create_checkpointer()
        graph = build_content_workflow(checkpointer=checkpointer)

        # Use same config as original execution
        config = {"configurable": {"thread_id": workflow_id}}

        # Update state with review_id before resuming
        graph.update_state(config, {"review_id": review_id})

        # Resume execution - LangGraph detects interrupt and continues
        # This will continue from review_gate_node to platform publishing
        logger.info(f"Invoking graph to resume from interrupt: {workflow_id}")

        # Stream the resumed workflow with retry logic (continues where it left off)
        try:
            async for update in graph.astream(None, config=config):
                node_name = list(update.keys())[0] if update else "unknown"
                logger.info(f"Resumed workflow node completed: {node_name}")

                # Broadcast updates via WebSocket
                await ws_manager.broadcast_to_workflow(
                    workflow_id,
                    node_completed_message(workflow_id, node_name, update.get(node_name, {}))
                )

            logger.info(f"✅ Workflow {workflow_id} resumed and completed successfully")

        except Exception as stream_error:
            logger.error(f"Resume stream failed: {stream_error}, retrying in 5s")
            import asyncio
            await asyncio.sleep(5)

            # Retry resume with exponential backoff
            try:
                async for update in graph.astream(None, config=config):
                    node_name = list(update.keys())[0] if update else "unknown"
                    logger.info(f"Retry resumed workflow node completed: {node_name}")

                    await ws_manager.broadcast_to_workflow(
                        workflow_id,
                        node_completed_message(workflow_id, node_name, update.get(node_name, {}))
                    )

                logger.info(f"✅ Workflow {workflow_id} resumed successfully after retry")
            except Exception as retry_error:
                raise retry_error  # Re-raise to be caught by outer handler

    except Exception as e:
        logger.error(f"❌ Failed to resume workflow {workflow_id}: {e}", exc_info=True)

        # Mark workflow as failed
        try:
            async with open_session() as session:
                workflow_uuid = uuid.UUID(workflow_id.replace("wf-", ""))
                result = await session.execute(
                    select(WorkflowExecution)
                    .where(WorkflowExecution.workflow_id == workflow_uuid)
                    .order_by(WorkflowExecution.created_at.desc())
                    .limit(1)
                )
                execution = result.scalars().first()
                if execution:
                    execution.status = "failed"
                    execution.error_message = f"Resume failed: {str(e)}"
                    await session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update database after resume error: {db_error}")


async def _handle_workflow_update(
    update: Dict[str, Any],
    workflow_id: str,
    thread_id: str,
    target_platforms: List[str]
):
    """
    Handle a single workflow update event from LangGraph stream.

    This function is PASSIVE - it receives events from LangGraph and:
    1. Broadcasts WebSocket updates
    2. Saves database checkpoints
    3. Posts conversational progress messages

    It does NOT orchestrate - LangGraph does all orchestration.

    Args:
        update: Event from LangGraph stream (node name + state)
        workflow_id: Workflow identifier
        thread_id: Thread identifier for progress messages
        target_platforms: Target platforms

    Returns:
        True if workflow completed, False if still running
    """
    from backend.workflow.supervisor_chat import save_progress_message

    node_name = update.get("node")
    state = update.get("state", {})

    logger.debug(f"📊 Workflow update: node={node_name}, workflow={workflow_id}")

    # Broadcast node completion via WebSocket
    await ws_manager.broadcast_to_workflow(
        workflow_id,
        node_completed_message(workflow_id, node_name, state)
    )

    # Update database checkpoint per node
    async with open_session() as session:
        workflow_uuid = uuid.UUID(workflow_id.replace("wf-", ""))
        result = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_id == workflow_uuid)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(1)
        )
        execution = result.scalars().first()
        if execution:
            execution.current_phase = node_name
            execution.total_cost_usd = state.get("total_cost_usd", execution.total_cost_usd)
            execution.cost_breakdown = state.get("cost_breakdown", execution.cost_breakdown)
            await session.commit()

    # Conversational progress updates (per-node messages)
    async with open_session() as session:
        if node_name == "supervisor":
            await save_progress_message(session, thread_id, "✅ Request validated and routed")
        elif node_name == "content_creation":
            await save_progress_message(session, thread_id, "✅ Script generated! Creating video now...")
        elif node_name == "tiktok":
            if state.get("publish_results", {}).get("tiktok", {}).get("status") == "success":
                await save_progress_message(session, thread_id, "📤 Published successfully to TikTok!")
        elif node_name == "youtube_shorts":
            if state.get("publish_results", {}).get("youtube_shorts", {}).get("status") == "success":
                await save_progress_message(session, thread_id, "📤 Published successfully to YouTube Shorts!")

    # Check if workflow completed (detected from LangGraph state)
    if state.get("workflow_status") in ["completed", "failed"]:
        await ws_manager.broadcast_to_workflow(
            workflow_id,
            workflow_completed_message(workflow_id, state)
        )

        # Final status message
        async with open_session() as session:
            if state.get("workflow_status") == "completed":
                total_cost = state.get("total_cost_usd", 0.0)
                video_path = state.get("video_path", "")
                publish_results = state.get("publish_results", {})

                # Build video URL for frontend - convert to relative path if needed
                video_url = video_path
                if video_path and "/videos/" in video_path:
                    # Extract relative path from absolute path (e.g., /app/videos/file.mp4 -> videos/file.mp4)
                    video_url = f"/videos/{video_path.split('/videos/')[-1]}"

                await save_progress_message(
                    session,
                    thread_id,
                    f"🎉 Workflow completed successfully! Total cost: ${total_cost:.2f}",
                    metadata={
                        "workflow_completed": True,
                        "workflow_id": workflow_id,
                        "video_url": video_url,
                        "publish_results": publish_results,
                        "total_cost_usd": total_cost
                    }
                )
            else:
                error = state.get("error_message", "Unknown error")
                await save_progress_message(
                    session,
                    thread_id,
                    f"❌ Workflow failed: {error}"
                )

        # Save final state to database
        await _save_workflow_execution(workflow_id, state)
        return True  # Signal completion

    return False  # Still running


async def execute_workflow_background(
    workflow_id: str,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    user_request: str,
    target_platforms: List[str],
    cost_limit_usd: float
):
    """
    Execute workflow in background with LangGraph orchestration.

    This is the SINGLE point of workflow execution for the entire system.

    CRITICAL ARCHITECTURE PRINCIPLE:
    - LangGraph stream_workflow() does ALL orchestration
    - This function ONLY handles side effects: WebSocket, database, messages
    - Zero custom routing logic - pure LangGraph delegation

    Flow:
    1. Update database: status="running"
    2. Send WebSocket: workflow_started
    3. Create PostgreSQL checkpointer
    4. Call LangGraph stream_workflow() ← DOES ALL ORCHESTRATION
    5. Handle each update event (passive - no routing)
    6. Save final results to database

    Args:
        workflow_id: Unique workflow identifier
        tenant_id: Tenant ID
        user_id: User ID
        thread_id: Thread ID for progress messages
        user_request: User's request
        target_platforms: Target platforms
        cost_limit_usd: Cost limit
    """
    from backend.workflow.supervisor_chat import save_progress_message

    logger.info(f"🚀 BACKGROUND EXECUTION STARTED: workflow={workflow_id}, thread={thread_id}, platforms={target_platforms}")

    execution_start_time = datetime.now(timezone.utc)

    try:
        # Update database: Set status to "running"
        async with open_session() as session:
            workflow_uuid = uuid.UUID(workflow_id.replace("wf-", ""))
            result = await session.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.workflow_id == workflow_uuid)
                .order_by(WorkflowExecution.created_at.desc())
                .limit(1)
            )
            execution = result.scalars().first()
            if execution:
                execution.status = "running"
                execution.current_phase = "starting"
                await session.commit()
                logger.info(f"✅ Updated workflow {workflow_id} status to 'running'")

        # Send workflow started event
        await ws_manager.broadcast_to_workflow(
            workflow_id,
            workflow_started_message(workflow_id, {
                "created_at": execution_start_time.isoformat(),
                "target_platforms": target_platforms,
                "cost_limit_usd": cost_limit_usd
            })
        )

        # Conversational update: Workflow started
        async with open_session() as session:
            await save_progress_message(
                session,
                thread_id,
                f"🚀 Starting workflow execution for {', '.join(target_platforms)}..."
            )

        # Create checkpointer (synchronous - no await, no context manager)
        try:
            checkpointer = create_checkpointer()
            logger.info("✅ PostgreSQL checkpointer created")
        except Exception as cp_error:
            logger.error(f"⚠️ Failed to create checkpointer: {cp_error}")
            checkpointer = None  # Fallback to in-memory

        # 🚀 CRITICAL: LangGraph does ALL orchestration here
        # This is a PASSIVE stream consumer - no routing logic
        if checkpointer:
            logger.info("🎯 Starting LangGraph stream with checkpointer")
            async for update in stream_workflow(
                workflow_id=workflow_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    user_request=user_request,
                    target_platforms=target_platforms,
                    cost_limit_usd=cost_limit_usd,
                    checkpointer=checkpointer
                ):
                    # PASSIVE: Just handle the update, don't orchestrate
                    is_complete = await _handle_workflow_update(
                        update, workflow_id, thread_id, target_platforms
                    )
                    if is_complete:
                        logger.info(f"✅ Workflow {workflow_id} completed (from LangGraph)")
                        break
        else:
            # Fallback: in-memory only (no checkpointer)
            logger.warning("⚠️ Running workflow without checkpointer (in-memory only)")
            async for update in stream_workflow(
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                user_id=user_id,
                thread_id=thread_id,
                user_request=user_request,
                target_platforms=target_platforms,
                cost_limit_usd=cost_limit_usd,
                checkpointer=None
            ):
                is_complete = await _handle_workflow_update(
                    update, workflow_id, thread_id, target_platforms
                )
                if is_complete:
                    logger.info(f"✅ Workflow {workflow_id} completed (from LangGraph)")
                    break

        execution_duration = (datetime.now(timezone.utc) - execution_start_time).total_seconds()
        logger.info(f"✅ Workflow execution completed: {workflow_id}, duration={execution_duration:.2f}s")

    except Exception as e:
        execution_duration = (datetime.now(timezone.utc) - execution_start_time).total_seconds()
        logger.error(
            f"❌ Workflow execution failed: {workflow_id}, error: {e}, duration: {execution_duration:.2f}s",
            exc_info=True
        )

        # Mark as failed in database
        try:
            async with open_session() as session:
                workflow_uuid = uuid.UUID(workflow_id.replace("wf-", ""))
                result = await session.execute(
                    select(WorkflowExecution)
                    .where(WorkflowExecution.workflow_id == workflow_uuid)
                    .order_by(WorkflowExecution.created_at.desc())
                    .limit(1)
                )
                execution = result.scalars().first()
                if execution:
                    execution.status = "failed"
                    execution.error_message = str(e)[:500]
                    execution.current_phase = "error"
                    await session.commit()
                    logger.info(f"✅ Marked workflow {workflow_id} as failed in database")
        except Exception as db_error:
            logger.error(f"❌ Failed to update database with error status: {db_error}")

        # Send error event
        await ws_manager.broadcast_to_workflow(
            workflow_id,
            workflow_error_message(workflow_id, str(e))
        )

        # Error notification message
        try:
            async with open_session() as session:
                error_msg = str(e)[:200]
                await save_progress_message(
                    session,
                    thread_id,
                    f"❌ Workflow execution error: {error_msg}"
                )
        except Exception as msg_error:
            logger.error(f"❌ Failed to save error message: {msg_error}")


async def _save_workflow_execution(workflow_id: str, final_state: Dict[str, Any]):
    """
    Save workflow execution results to database and semantic memory.

    Updates the WorkflowExecution record with final results and stores
    semantic insights to Mem0 for long-term learning.

    Args:
        workflow_id: Workflow ID
        final_state: Final workflow state from LangGraph
    """
    from backend.memory import MemoryManager

    try:
        async with open_session() as session:
            workflow_uuid = uuid.UUID(workflow_id.replace("wf-", ""))

            result = await session.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.workflow_id == workflow_uuid)
                .order_by(WorkflowExecution.created_at.desc())
                .limit(1)
            )
            execution = result.scalars().first()

            if execution:
                # Update existing execution record with final state
                execution.status = final_state.get("workflow_status", "completed")
                execution.trend_topic = final_state.get("trend_topic")
                execution.script = final_state.get("script")
                execution.video_path = final_state.get("video_path")
                execution.publish_results = final_state.get("publish_results", {})
                execution.cost_breakdown = final_state.get("cost_breakdown", {})
                execution.total_cost_usd = final_state.get("total_cost_usd", 0.0)
                execution.error_message = final_state.get("error_message")
                execution.completed_at = datetime.now(timezone.utc)

                await session.commit()
                logger.info(f"✅ Workflow execution saved to PostgreSQL: {workflow_id}")

            # 🧠 SEMANTIC MEMORY: Store workflow insights to Mem0
            try:
                tenant_id = final_state.get("tenant_id", "default")
                user_id = final_state.get("user_id", "default")
                platforms = final_state.get("target_platforms", [])
                status = final_state.get("workflow_status", "unknown")
                cost = final_state.get("total_cost_usd", 0.0)

                memory = MemoryManager(tenant_id=tenant_id, agent_id="supervisor")

                # Store semantic fact (NOT raw conversation)
                semantic_insight = (
                    f"Workflow {workflow_id[:8]} for {', '.join(platforms)}: "
                    f"Status={status}, Cost=${cost:.2f}, "
                    f"Request='{final_state.get('user_request', '')[:100]}'"
                )

                memory.add_fact(
                    user_id=user_id,
                    text=semantic_insight,
                    score=1.0 if status == "completed" else -0.5,
                    category="workflow_outcome",
                    tags=platforms + [status, f"cost_${int(cost)}"]
                )

                metrics = memory.get_metrics()
                logger.info(
                    f"✅ Memory consolidation complete: "
                    f"namespace={metrics['namespace']}, "
                    f"mem0_enabled={metrics['mem0_enabled']}"
                )

            except Exception as mem_error:
                logger.warning(f"⚠️ Failed to store semantic memory: {mem_error}")
                # Don't fail the workflow if memory storage fails

    except Exception as e:
        logger.error(f"❌ Failed to save workflow execution: {e}", exc_info=True)
