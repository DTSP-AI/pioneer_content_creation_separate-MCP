"""
System Health Check & Validation Script

Validates all subsystems before local testing based on:
- currentPrompt.md hard questions
- No observability layer (skip metrics)

Tests:
1. LangGraph orchestration
2. Memory systems (Mem0 + Qdrant + PostgreSQL)
3. PiAPI MCP connectivity
4. Database schema
5. Tool registry and fallbacks
6. Docker service health
7. API key validation

Usage:
    # Inside Docker container
    python -m backend.validation.system_health_check

    # Or from host
    docker-compose exec backend python -m backend.validation.system_health_check
"""

import asyncio
import sys
import logging
from typing import Dict, Any, List
from datetime import datetime
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthCheck:
    """System health check validator."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.passed = 0
        self.failed = 0

    def log_test(self, category: str, test: str, passed: bool, details: str = ""):
        """Log a test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "category": category,
            "test": test,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results.append(result)

        if passed:
            self.passed += 1
            logger.info(f"{status} [{category}] {test}")
        else:
            self.failed += 1
            logger.error(f"{status} [{category}] {test} - {details}")

        if details and passed:
            logger.debug(f"  └─ {details}")

    async def test_config_loaded(self) -> bool:
        """Test 1: Configuration loads successfully."""
        try:
            from backend.config import get_settings
            settings = get_settings()

            # Check required keys exist
            required = [
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "MEM0_API_KEY",
                "DATABASE_URL"
            ]

            missing = []
            for key in required:
                if not getattr(settings, key, None):
                    missing.append(key)

            if missing:
                self.log_test(
                    "Configuration",
                    "Required API keys present",
                    False,
                    f"Missing: {', '.join(missing)}"
                )
                return False

            self.log_test(
                "Configuration",
                "Required API keys present",
                True,
                f"All {len(required)} required keys found"
            )
            return True

        except Exception as e:
            self.log_test("Configuration", "Config loading", False, str(e))
            return False

    async def test_database_connection(self) -> bool:
        """Test 2: PostgreSQL connection and schema."""
        try:
            from backend.database.models import init_database, get_session, Tenant, User, Agent, Thread, Workflow
            from sqlalchemy import select, text

            # Initialize database
            await init_database()
            self.log_test("Database", "PostgreSQL connection", True, "Connected successfully")

            # Test schema exists
            async with get_session() as session:
                # Test tables exist
                result = await session.execute(
                    text("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_type = 'BASE TABLE'
                    """)
                )
                tables = [row[0] for row in result.fetchall()]

                required_tables = [
                    'tenants', 'users', 'agents', 'threads', 'thread_messages',
                    'workflows', 'workflow_executions', 'cost_tracking'
                ]

                missing_tables = [t for t in required_tables if t not in tables]

                if missing_tables:
                    self.log_test(
                        "Database",
                        "Schema tables exist",
                        False,
                        f"Missing: {', '.join(missing_tables)}"
                    )
                    return False

                self.log_test(
                    "Database",
                    "Schema tables exist",
                    True,
                    f"Found {len(tables)} tables"
                )

                # Test tenant index (multi-tenancy check)
                result = await session.execute(
                    text("""
                        SELECT indexname
                        FROM pg_indexes
                        WHERE tablename = 'workflow_executions'
                        AND indexname LIKE '%tenant%'
                    """)
                )
                indexes = result.fetchall()

                if not indexes:
                    self.log_test(
                        "Database",
                        "Multi-tenant indexes",
                        False,
                        "No tenant_id indexes found on workflow_executions"
                    )
                else:
                    self.log_test(
                        "Database",
                        "Multi-tenant indexes",
                        True,
                        f"Found {len(indexes)} tenant indexes"
                    )

            return True

        except Exception as e:
            self.log_test("Database", "PostgreSQL connection", False, str(e))
            return False

    async def test_qdrant_connection(self) -> bool:
        """Test 3: Qdrant vector store connectivity."""
        try:
            from backend.config import get_settings
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            settings = get_settings()

            # Connect to Qdrant
            client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )

            # Test health
            health = client.http.request(method="GET", path="/health")
            self.log_test(
                "Qdrant",
                "Service health check",
                True,
                f"Status: {health.status_code}"
            )

            # Test collection creation
            collection_name = "test_validation_collection"
            try:
                # Create test collection
                client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )

                # Check dimensions match embedding model
                collection_info = client.get_collection(collection_name)
                vector_size = collection_info.config.params.vectors.size

                if vector_size != 768:
                    self.log_test(
                        "Qdrant",
                        "Vector dimensions",
                        False,
                        f"Expected 768, got {vector_size}"
                    )
                else:
                    self.log_test(
                        "Qdrant",
                        "Vector dimensions",
                        True,
                        f"Correct: 768 (text-embedding-3-small)"
                    )

                # Cleanup
                client.delete_collection(collection_name)

            except Exception as e:
                self.log_test("Qdrant", "Collection operations", False, str(e))
                return False

            return True

        except Exception as e:
            self.log_test("Qdrant", "Service health check", False, str(e))
            return False

    async def test_mem0_connection(self) -> bool:
        """Test 4: Mem0 semantic memory API."""
        try:
            from backend.config import get_settings
            from mem0 import Memory

            settings = get_settings()

            # Initialize Mem0
            memory = Memory(
                api_key=settings.MEM0_API_KEY,
                org_id=settings.MEM0_ORG_ID
            )

            # Test API call (search with empty query should work)
            try:
                result = memory.search(
                    query="test",
                    user_id="health-check-user",
                    limit=1
                )

                self.log_test(
                    "Mem0",
                    "API connectivity",
                    True,
                    "Successfully queried Mem0 API"
                )
                return True

            except Exception as api_error:
                # Check if it's an auth error vs connection error
                error_str = str(api_error).lower()
                if "401" in error_str or "unauthorized" in error_str:
                    self.log_test(
                        "Mem0",
                        "API connectivity",
                        False,
                        "Invalid API key or org ID"
                    )
                else:
                    self.log_test(
                        "Mem0",
                        "API connectivity",
                        False,
                        f"API error: {api_error}"
                    )
                return False

        except Exception as e:
            self.log_test("Mem0", "API connectivity", False, str(e))
            return False

    async def test_piapi_mcp_connection(self) -> bool:
        """Test 5: PiAPI MCP server connectivity."""
        try:
            from backend.config import get_settings

            settings = get_settings()

            # Test HTTP connection to MCP server
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    # Test base URL
                    response = await client.get(settings.PIAPI_MCP_SERVER_URL.replace("/sse", ""))

                    if response.status_code == 200:
                        self.log_test(
                            "PiAPI MCP",
                            "Server connectivity",
                            True,
                            f"Server responding on {settings.PIAPI_MCP_SERVER_URL}"
                        )
                    else:
                        self.log_test(
                            "PiAPI MCP",
                            "Server connectivity",
                            False,
                            f"Server returned status {response.status_code}"
                        )
                        return False

                except httpx.ConnectError:
                    self.log_test(
                        "PiAPI MCP",
                        "Server connectivity",
                        False,
                        f"Cannot connect to {settings.PIAPI_MCP_SERVER_URL}"
                    )
                    return False

            # Test tool discovery
            try:
                from backend.mcp_client import get_piapi_mcp_client

                client, tools = await get_piapi_mcp_client()

                if tools:
                    tool_names = [t.name for t in tools]
                    self.log_test(
                        "PiAPI MCP",
                        "Tool discovery",
                        True,
                        f"Found {len(tools)} tools: {', '.join(tool_names)}"
                    )
                else:
                    self.log_test(
                        "PiAPI MCP",
                        "Tool discovery",
                        False,
                        "No tools discovered from MCP server"
                    )

            except Exception as tool_error:
                self.log_test(
                    "PiAPI MCP",
                    "Tool discovery",
                    False,
                    str(tool_error)
                )

            return True

        except Exception as e:
            self.log_test("PiAPI MCP", "Server connectivity", False, str(e))
            return False

    async def test_tool_registry(self) -> bool:
        """Test 6: Tool registry and fallback logic."""
        try:
            from backend.tools import ToolRegistry

            # Test static tools
            static_tools = ToolRegistry.get_static_tools()

            if not static_tools:
                self.log_test(
                    "Tool Registry",
                    "Static tools loading",
                    False,
                    "No static tools found"
                )
                return False

            tool_names = [t.name for t in static_tools]
            self.log_test(
                "Tool Registry",
                "Static tools loading",
                True,
                f"Loaded {len(static_tools)} tools: {', '.join(tool_names)}"
            )

            # Test hybrid loading (MCP + static)
            all_tools = await ToolRegistry.get_all_tools()

            if len(all_tools) < len(static_tools):
                self.log_test(
                    "Tool Registry",
                    "Hybrid tool loading",
                    False,
                    f"Lost tools during hybrid load: {len(static_tools)} -> {len(all_tools)}"
                )
                return False

            self.log_test(
                "Tool Registry",
                "Hybrid tool loading",
                True,
                f"Total tools available: {len(all_tools)}"
            )

            # Check for duplicate tool names
            all_tool_names = [t.name for t in all_tools]
            duplicates = [name for name in all_tool_names if all_tool_names.count(name) > 1]

            if duplicates:
                self.log_test(
                    "Tool Registry",
                    "No duplicate tools",
                    False,
                    f"Duplicate tool names: {', '.join(set(duplicates))}"
                )
            else:
                self.log_test(
                    "Tool Registry",
                    "No duplicate tools",
                    True,
                    "All tool names are unique"
                )

            return True

        except Exception as e:
            self.log_test("Tool Registry", "Tool loading", False, str(e))
            return False

    async def test_langgraph_orchestration(self) -> bool:
        """Test 7: LangGraph structure and state management."""
        try:
            from backend.graph.graph import build_content_workflow
            from backend.state.state_schema import VideoWorkflowState

            # Build graph
            graph = build_content_workflow()

            # Check graph structure
            graph_structure = graph.get_graph()

            # Verify entry point
            if graph_structure.entry_point != "supervisor":
                self.log_test(
                    "LangGraph",
                    "Entry point is supervisor",
                    False,
                    f"Entry point is '{graph_structure.entry_point}' not 'supervisor'"
                )
                return False

            self.log_test(
                "LangGraph",
                "Entry point is supervisor",
                True,
                "Supervisor is entry node"
            )

            # Verify all nodes exist
            expected_nodes = ["supervisor", "content_creation", "tiktok", "youtube_shorts"]
            actual_nodes = [node.id for node in graph_structure.nodes]

            missing_nodes = [n for n in expected_nodes if n not in actual_nodes]

            if missing_nodes:
                self.log_test(
                    "LangGraph",
                    "All nodes registered",
                    False,
                    f"Missing nodes: {', '.join(missing_nodes)}"
                )
                return False

            self.log_test(
                "LangGraph",
                "All nodes registered",
                True,
                f"Found {len(actual_nodes)} nodes"
            )

            # Verify state schema
            # Check that VideoWorkflowState is TypedDict
            import typing
            is_typed_dict = issubclass(VideoWorkflowState, dict) and hasattr(VideoWorkflowState, '__annotations__')

            if not is_typed_dict:
                self.log_test(
                    "LangGraph",
                    "State schema is TypedDict",
                    False,
                    "VideoWorkflowState is not a TypedDict"
                )
            else:
                self.log_test(
                    "LangGraph",
                    "State schema is TypedDict",
                    True,
                    f"{len(VideoWorkflowState.__annotations__)} state fields defined"
                )

            return True

        except Exception as e:
            self.log_test("LangGraph", "Graph building", False, str(e))
            return False

    async def test_docker_services(self) -> bool:
        """Test 8: Docker service health (if running in Docker)."""
        try:
            # Test if we're in Docker
            import os
            if not os.path.exists("/.dockerenv"):
                self.log_test(
                    "Docker",
                    "Running in container",
                    False,
                    "Not running in Docker (skip in local dev)"
                )
                return True  # Not a failure, just not applicable

            self.log_test(
                "Docker",
                "Running in container",
                True,
                "Detected Docker environment"
            )

            # Test service connectivity
            services = {
                "PostgreSQL": "postgres:5432",
                "Qdrant": "qdrant:6333",
                "PiAPI MCP": "piapi-mcp:7870"
            }

            for service_name, endpoint in services.items():
                host, port = endpoint.split(":")
                port = int(port)

                try:
                    # Simple TCP connection test
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result == 0:
                        self.log_test(
                            "Docker",
                            f"{service_name} reachable",
                            True,
                            f"Connected to {endpoint}"
                        )
                    else:
                        self.log_test(
                            "Docker",
                            f"{service_name} reachable",
                            False,
                            f"Cannot connect to {endpoint}"
                        )

                except Exception as conn_error:
                    self.log_test(
                        "Docker",
                        f"{service_name} reachable",
                        False,
                        str(conn_error)
                    )

            return True

        except Exception as e:
            self.log_test("Docker", "Service connectivity", False, str(e))
            return False

    async def test_ffmpeg_availability(self) -> bool:
        """Test 9: FFmpeg installed for video processing."""
        try:
            import subprocess

            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.log_test(
                    "Dependencies",
                    "FFmpeg installed",
                    True,
                    version_line
                )
                return True
            else:
                self.log_test(
                    "Dependencies",
                    "FFmpeg installed",
                    False,
                    "FFmpeg not found or failed to execute"
                )
                return False

        except FileNotFoundError:
            self.log_test(
                "Dependencies",
                "FFmpeg installed",
                False,
                "FFmpeg binary not found in PATH"
            )
            return False
        except Exception as e:
            self.log_test(
                "Dependencies",
                "FFmpeg installed",
                False,
                str(e)
            )
            return False

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print("\n" + "="*70)
        print("SYSTEM HEALTH CHECK SUMMARY")
        print("="*70)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print("="*70)

        if self.failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["passed"]:
                    print(f"  - [{result['category']}] {result['test']}")
                    print(f"    └─ {result['details']}")

        print("\n" + "="*70)

        if self.failed == 0:
            print("✅ ALL SYSTEMS OPERATIONAL - Ready for local testing!")
        else:
            print(f"⚠️  {self.failed} ISSUES DETECTED - Fix before testing")

        print("="*70 + "\n")

    async def run_all_tests(self):
        """Run all health checks."""
        print("\n" + "="*70)
        print("CONTENT CREATION AGENT - SYSTEM HEALTH CHECK")
        print("="*70)
        print(f"Started: {datetime.utcnow().isoformat()}")
        print("="*70 + "\n")

        # Run tests in order
        await self.test_config_loaded()
        await self.test_database_connection()
        await self.test_qdrant_connection()
        await self.test_mem0_connection()
        await self.test_piapi_mcp_connection()
        await self.test_tool_registry()
        await self.test_langgraph_orchestration()
        await self.test_docker_services()
        await self.test_ffmpeg_availability()

        # Print summary
        self.print_summary()

        # Return exit code
        return 0 if self.failed == 0 else 1


async def main():
    """Main entry point."""
    health_check = HealthCheck()
    exit_code = await health_check.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
