"""
PiAPI MCP Client

Connects to PiAPI MCP Server via Server-Sent Events (SSE) to access advanced
video generation tools through the Model Context Protocol.

This implementation uses the official MCP SDK to establish a proper connection
and dynamically discover tools from the server.

Architecture:
- Connects to local PiAPI MCP server (Node.js/TypeScript) via SSE
- Uses MCP SDK for protocol-compliant communication
- Dynamically discovers available tools via MCP list_tools
- Converts MCP tools to LangChain-compatible tools
- Caches client connection for reuse
"""

from typing import List, Optional, Tuple, Any, Dict
import logging
import json
import asyncio
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Implementation
from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field, create_model

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Global client cache (singleton pattern)
_piapi_mcp_client: Optional['PiAPIMCPClient'] = None


class PiAPIMCPClient:
    """
    PiAPI MCP Client - Connects to PiAPI MCP server via MCP protocol.

    Manages connection lifecycle and tool retrieval from the MCP server
    using the official MCP SDK.

    Usage:
        async with PiAPIMCPClient() as client:
            tools = await client.get_tools()
    """

    def __init__(
        self,
        server_url: Optional[str] = None
    ):
        """
        Initialize PiAPI MCP client.

        Args:
            server_url: MCP server URL (defaults to config)

        Note:
            No API key needed here - the MCP server handles PiAPI authentication
            using credentials from PiAPI_MCP/piapi-mcp-server/.env.local
        """
        self.server_url = server_url or settings.PIAPI_MCP_SERVER_URL
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._connection_task = None  # Background task keeping SSE alive
        self._connection_error = None  # Store any connection errors
        self.tools: List[Tool] = []
        self._connected = False
        self._connection_ready = asyncio.Event()  # Signal when connection is ready

    async def __aenter__(self):
        """Enter async context manager - establishes connection."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - closes connection."""
        await self.close()
        return False

    async def _maintain_connection(self) -> None:
        """
        Background task that maintains the SSE connection using proper async with.

        This keeps the SSE context manager alive throughout the client's lifetime,
        preventing "cancel scope in different task" errors.
        """
        try:
            logger.info(f"Connecting to PiAPI MCP server: {self.server_url}")

            # Use async with to properly manage SSE lifecycle
            async with sse_client(
                url=self.server_url,
                timeout=10.0,
                sse_read_timeout=300.0
            ) as (read_stream, write_stream):
                # Store streams
                self.read_stream = read_stream
                self.write_stream = write_stream

                # Initialize MCP session with proper client info
                client_info = Implementation(
                    name="content-creation-agent",
                    version="1.0.0"
                )
                self.session = ClientSession(
                    read_stream,
                    write_stream,
                    client_info=client_info
                )

                # Initialize the MCP protocol handshake
                logger.info("Initiating MCP protocol handshake...")
                try:
                    init_result = await asyncio.wait_for(
                        self.session.initialize(),
                        timeout=5.0
                    )
                    logger.info(f"✅ MCP handshake complete - Protocol: {init_result.protocol_version}")
                    logger.info(f"Server: {init_result.server_info}")
                except asyncio.TimeoutError:
                    logger.warning("MCP initialize() timed out - proceeding anyway")
                except Exception as e:
                    logger.warning(f"MCP initialize() failed: {e} - proceeding anyway")

                # Mark as connected and signal readiness
                self._connected = True
                self._connection_ready.set()
                logger.info("MCP client ready")

                # Keep the connection alive until cancelled
                logger.info("MCP connection active, waiting for close signal...")
                await asyncio.Event().wait()  # Wait forever (until task cancelled)

        except asyncio.CancelledError:
            logger.info("MCP connection task cancelled gracefully")
            raise
        except Exception as e:
            logger.error(f"SSE connection failed: {e}")
            logger.exception("Full traceback:")
            self._connection_error = e
            self._connection_ready.set()  # Unblock any waiters
            raise
        finally:
            self._connected = False
            logger.info("SSE connection closed")

    async def connect(self) -> None:
        """
        Connect to PiAPI MCP server by starting background SSE task.

        Waits for connection to be ready before returning.
        """
        if self._connection_task and not self._connection_task.done():
            logger.warning("Connection task already running")
            return

        # Reset state
        self._connection_ready.clear()
        self._connection_error = None

        # Start background task
        self._connection_task = asyncio.create_task(self._maintain_connection())

        # Wait for connection to be ready (with timeout)
        try:
            await asyncio.wait_for(self._connection_ready.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            self._connection_task.cancel()
            raise ConnectionError("MCP connection timeout - server did not respond within 10s")

        # Check if connection failed
        if self._connection_error:
            raise ConnectionError(f"MCP connection failed: {self._connection_error}")

    async def get_tools(self) -> List[Tool]:
        """
        Retrieve tools from PiAPI MCP server via MCP protocol.

        Discovers available tools dynamically using session.list_tools()
        and converts them to LangChain-compatible Tool objects.

        Returns:
            List of LangChain-compatible tools

        Raises:
            RuntimeError: If not connected
        """
        if not self._connected or not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            logger.info("Discovering tools from PiAPI MCP server via MCP protocol...")

            # Use MCP SDK to list available tools
            tools_response = await self.session.list_tools()

            logger.info(f"MCP server reported {len(tools_response.tools)} tools")

            # Convert MCP tools to LangChain tools
            self.tools = []
            for mcp_tool in tools_response.tools:
                try:
                    langchain_tool = await self._convert_mcp_tool_to_langchain(mcp_tool)
                    self.tools.append(langchain_tool)
                    logger.debug(f"Converted MCP tool: {mcp_tool.name}")
                except Exception as e:
                    logger.error(f"Failed to convert tool {mcp_tool.name}: {e}")
                    continue

            logger.info(f"Successfully converted {len(self.tools)} MCP tools to LangChain format")

            return self.tools

        except Exception as e:
            logger.error(f"Failed to retrieve MCP tools: {e}")
            logger.exception("Full traceback:")
            return []

    async def _convert_mcp_tool_to_langchain(self, mcp_tool) -> Tool:
        """
        Convert an MCP tool to a LangChain Tool.

        Args:
            mcp_tool: MCP tool definition from list_tools response

        Returns:
            LangChain Tool object
        """
        tool_name = mcp_tool.name
        tool_description = mcp_tool.description or f"MCP tool: {tool_name}"

        # Extract input schema from MCP tool
        input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}

        # Create async function that calls the MCP tool
        async def invoke_mcp_tool(**kwargs) -> str:
            """
            Invoke MCP tool via session.call_tool().

            Args:
                **kwargs: Tool arguments

            Returns:
                JSON string with tool result
            """
            try:
                logger.info(f"Invoking MCP tool: {tool_name} with args: {kwargs}")

                # Call tool via MCP protocol
                result = await self.session.call_tool(
                    name=tool_name,
                    arguments=kwargs
                )

                logger.info(f"MCP tool {tool_name} completed successfully")

                # Parse result
                # MCP returns CallToolResult with content array
                if hasattr(result, 'content') and result.content:
                    # Extract text content from first item
                    content_item = result.content[0]
                    if hasattr(content_item, 'text'):
                        return content_item.text
                    elif hasattr(content_item, 'data'):
                        return json.dumps(content_item.data)
                    else:
                        return str(content_item)

                return json.dumps({"status": "success", "result": str(result)})

            except Exception as e:
                logger.error(f"MCP tool {tool_name} failed: {e}")
                logger.exception("Full traceback:")
                return json.dumps({
                    "status": "error",
                    "error": str(e),
                    "tool": tool_name
                })

        # Create sync wrapper for LangChain compatibility
        def invoke_mcp_tool_sync(**kwargs) -> str:
            """Sync wrapper that runs async function."""
            return asyncio.run(invoke_mcp_tool(**kwargs))

        # Create Pydantic model for input schema if available
        if input_schema and isinstance(input_schema, dict) and input_schema.get('properties'):
            try:
                # Build Pydantic model from JSON schema
                fields = {}
                properties = input_schema.get('properties', {})
                required_fields = input_schema.get('required', [])

                for field_name, field_spec in properties.items():
                    field_type = self._json_schema_type_to_python(field_spec)
                    field_description = field_spec.get('description', '')
                    is_required = field_name in required_fields

                    if is_required:
                        fields[field_name] = (field_type, Field(description=field_description))
                    else:
                        fields[field_name] = (Optional[field_type], Field(default=None, description=field_description))

                # Create dynamic Pydantic model
                input_model = create_model(
                    f"{tool_name}_input",
                    **fields
                )

                # Use StructuredTool with schema
                return StructuredTool(
                    name=tool_name,
                    description=tool_description,
                    func=invoke_mcp_tool_sync,
                    coroutine=invoke_mcp_tool,
                    args_schema=input_model
                )

            except Exception as e:
                logger.warning(f"Failed to create structured schema for {tool_name}: {e}")
                # Fall back to basic Tool

        # Fallback: Create basic Tool without structured input
        return Tool(
            name=tool_name,
            description=tool_description,
            func=invoke_mcp_tool_sync,
            coroutine=invoke_mcp_tool
        )

    def _json_schema_type_to_python(self, schema: Dict[str, Any]) -> type:
        """
        Convert JSON Schema type to Python type.

        Args:
            schema: JSON schema field definition

        Returns:
            Python type
        """
        schema_type = schema.get('type', 'string')

        type_mapping = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }

        return type_mapping.get(schema_type, str)

    async def _cleanup_connection(self) -> None:
        """Cleanup SSE connection resources by cancelling background task."""
        try:
            if self._connection_task and not self._connection_task.done():
                logger.debug("Cancelling MCP connection background task")
                self._connection_task.cancel()
                try:
                    await self._connection_task
                except asyncio.CancelledError:
                    pass  # Expected
                logger.debug("MCP connection task stopped")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {e}")

    async def close(self) -> None:
        """Close MCP client connection."""
        try:
            if self.session:
                # No explicit close needed for ClientSession
                self.session = None

            # Exit SSE context manager properly
            await self._cleanup_connection()

            self.read_stream = None
            self.write_stream = None
            self._connected = False

            logger.info("PiAPI MCP client connection closed")

        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")


# =============================================================================
# Convenience Functions
# =============================================================================

async def get_piapi_mcp_client() -> Tuple[Optional[PiAPIMCPClient], List[Tool]]:
    """
    Get or create PiAPI MCP client singleton (lazy initialization).

    Returns:
        Tuple of (client, tools)

    Usage:
        client, tools = await get_piapi_mcp_client()

    Note:
        - Initializes on first call (lazy loading)
        - Safe to call multiple times - returns cached client
        - Fails gracefully with timeout protection
        - Call close_piapi_mcp_client() during shutdown
    """
    global _piapi_mcp_client

    # Check if MCP is enabled
    if not settings.PIAPI_MCP_ENABLED:
        logger.warning("PiAPI MCP is disabled in config")
        return None, []

    # Return cached client if available and connected
    if _piapi_mcp_client is not None and _piapi_mcp_client._connected:
        logger.debug("Reusing existing PiAPI MCP client")
        return _piapi_mcp_client, _piapi_mcp_client.tools

    # Lazy initialization - first call only
    logger.info("🔄 Initializing PiAPI MCP client (lazy load)...")

    try:
        client = PiAPIMCPClient()

        # Connect with timeout to prevent blocking
        await asyncio.wait_for(client.connect(), timeout=15.0)
        tools = await client.get_tools()

        # Cache for reuse - client stays open
        _piapi_mcp_client = client

        logger.info(f"✅ PiAPI MCP client initialized successfully with {len(tools)} tools")

        return client, tools

    except asyncio.TimeoutError:
        logger.warning("⚠️ MCP initialization timed out after 15s - continuing without MCP tools")
        logger.info("Application will use fallback video generation tools")
        return None, []

    except ConnectionError as e:
        logger.warning(f"⚠️ MCP connection failed: {e}")
        logger.info("Application will use fallback video generation tools")
        return None, []

    except Exception as e:
        logger.error(f"❌ Unexpected error initializing MCP client: {e}")
        logger.exception("Full traceback:")
        logger.info("Application will use fallback video generation tools")
        return None, []


async def close_piapi_mcp_client() -> None:
    """
    Close global PiAPI MCP client connection.

    Call this during application shutdown.
    """
    global _piapi_mcp_client

    if _piapi_mcp_client:
        await _piapi_mcp_client.close()
        _piapi_mcp_client = None
        logger.info("Global PiAPI MCP client closed")
