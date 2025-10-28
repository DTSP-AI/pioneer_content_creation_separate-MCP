"""
WebSocket Manager

Manages WebSocket connections for real-time workflow updates.
Broadcasts state changes from LangGraph stream to connected clients.

Architecture Compliance:
- Async/await for non-blocking connections
- Connection pooling per workflow_id
- Graceful error handling
- JSON serialization for state updates
"""

from typing import Dict, Set, Any
import logging
import json
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for workflow streaming.

    Features:
    - Multiple clients per workflow
    - Automatic connection cleanup
    - Broadcast to all clients watching a workflow
    - Error isolation (one client error doesn't affect others)
    """

    def __init__(self):
        # workflow_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """
        Accept new WebSocket connection for a workflow.

        Args:
            websocket: FastAPI WebSocket instance
            workflow_id: Workflow to subscribe to
        """
        await websocket.accept()

        async with self._lock:
            if workflow_id not in self.active_connections:
                self.active_connections[workflow_id] = set()
            self.active_connections[workflow_id].add(websocket)

        logger.info(
            f"WebSocket connected: workflow={workflow_id}, "
            f"total_connections={len(self.active_connections[workflow_id])}"
        )

    async def disconnect(self, websocket: WebSocket, workflow_id: str):
        """
        Remove WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            workflow_id: Workflow being watched
        """
        async with self._lock:
            if workflow_id in self.active_connections:
                self.active_connections[workflow_id].discard(websocket)

                # Clean up empty sets
                if not self.active_connections[workflow_id]:
                    del self.active_connections[workflow_id]

        logger.info(f"WebSocket disconnected: workflow={workflow_id}")

    async def broadcast_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """
        Broadcast message to all clients watching a workflow.

        Args:
            workflow_id: Target workflow
            message: JSON-serializable message dict
        """
        if workflow_id not in self.active_connections:
            logger.debug(f"No connections for workflow: {workflow_id}")
            return

        # Create copy to avoid modification during iteration
        connections = list(self.active_connections.get(workflow_id, []))

        if not connections:
            return

        logger.debug(
            f"Broadcasting to {len(connections)} clients: "
            f"workflow={workflow_id}, event={message.get('event')}"
        )

        # Broadcast to all connections (with error isolation)
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(websocket)
                logger.warning(f"Client disconnected during broadcast: workflow={workflow_id}")
            except Exception as e:
                disconnected.append(websocket)
                logger.error(f"Error sending to WebSocket: {e}", exc_info=True)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    if workflow_id in self.active_connections:
                        self.active_connections[workflow_id].discard(ws)

                # Clean up empty sets
                if workflow_id in self.active_connections and not self.active_connections[workflow_id]:
                    del self.active_connections[workflow_id]

    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send message to a specific client.

        Args:
            websocket: Target WebSocket
            message: JSON-serializable message dict
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to client: {e}", exc_info=True)

    def get_connection_count(self, workflow_id: str = None) -> int:
        """
        Get number of active connections.

        Args:
            workflow_id: Specific workflow (None for total)

        Returns:
            Connection count
        """
        if workflow_id:
            return len(self.active_connections.get(workflow_id, set()))

        return sum(len(conns) for conns in self.active_connections.values())

    async def close_all_for_workflow(self, workflow_id: str):
        """
        Close all connections for a workflow.

        Used when workflow completes or fails.

        Args:
            workflow_id: Workflow to close connections for
        """
        if workflow_id not in self.active_connections:
            return

        connections = list(self.active_connections.get(workflow_id, []))

        for websocket in connections:
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")

        async with self._lock:
            if workflow_id in self.active_connections:
                del self.active_connections[workflow_id]

        logger.info(f"Closed {len(connections)} connections for workflow: {workflow_id}")


# Global WebSocket manager instance
ws_manager = WebSocketManager()


# Message helpers for common events
def workflow_started_message(workflow_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Create workflow started message."""
    return {
        "event": "workflow_started",
        "workflow_id": workflow_id,
        "timestamp": config.get("created_at"),
        "target_platforms": config.get("target_platforms", []),
        "cost_limit_usd": config.get("cost_limit_usd", 5.0)
    }


def node_started_message(workflow_id: str, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Create node started message."""
    return {
        "event": "node_started",
        "workflow_id": workflow_id,
        "node": node_name,
        "current_agent": state.get("current_agent"),
        "workflow_phase": state.get("workflow_phase"),
        "timestamp": state.get("updated_at")
    }


def node_completed_message(workflow_id: str, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Create node completed message."""
    return {
        "event": "node_completed",
        "workflow_id": workflow_id,
        "node": node_name,
        "current_agent": state.get("current_agent"),
        "workflow_phase": state.get("workflow_phase"),
        "workflow_status": state.get("workflow_status"),
        "total_cost_usd": state.get("total_cost_usd", 0),
        "timestamp": state.get("updated_at")
    }


def workflow_completed_message(workflow_id: str, final_state: Dict[str, Any]) -> Dict[str, Any]:
    """Create workflow completed message."""
    return {
        "event": "workflow_completed",
        "workflow_id": workflow_id,
        "status": final_state.get("workflow_status"),
        "publish_results": final_state.get("publish_results", {}),
        "total_cost_usd": final_state.get("total_cost_usd", 0),
        "cost_breakdown": final_state.get("cost_breakdown", {}),
        "video_url": final_state.get("video_path"),
        "timestamp": final_state.get("updated_at")
    }


def workflow_error_message(workflow_id: str, error: str, state: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create workflow error message."""
    return {
        "event": "workflow_error",
        "workflow_id": workflow_id,
        "error": error,
        "current_agent": state.get("current_agent") if state else None,
        "workflow_phase": state.get("workflow_phase") if state else None,
        "timestamp": state.get("updated_at") if state else None
    }
