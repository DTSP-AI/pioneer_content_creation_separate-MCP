"""
Mem0 + Qdrant Memory Manager for Content Creation System

This module provides a hybrid memory management interface combining:
1. Mem0 - Cloud-based semantic memory for long-term context
2. Qdrant - Multi-tenant vector store for conversation history

Architecture Compliance:
- Follows AGENT_CREATION_STANDARD.md + AGENT_ORCHESTRATION_STANDARD.md
- Namespace isolation: {tenant_id}:{agent_id}:thread:{thread_id}
- Multi-tenant vector storage with Qdrant
- Async-first API for LangGraph integration
- Cross-chat memory retrieval for campaign history

Pattern adopted from mcp-voice-agent example:
- MultiTenantVectorStore for conversation history
- Mem0 for semantic long-term memory
- PostgreSQL for structured thread messages
"""

from typing import Any, Dict, List, Optional
import os
import logging
from datetime import datetime

from mem0 import Memory
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models
from langchain_qdrant import QdrantVectorStore

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryManager:
    """
    Hybrid Mem0 + Qdrant memory manager for multi-agent workflows.

    This manager combines:
    1. Mem0 - Long-term semantic memory (agent facts, preferences, learnings)
    2. Qdrant - Multi-tenant conversation history (thread-based chat logs)
    3. PostgreSQL - Structured thread messages (for database queries)

    Architecture:
    - Stores all agent interactions in BOTH Mem0 (semantic) and Qdrant (vector)
    - Retrieves relevant context via dual-path search
    - Maintains namespace isolation per tenant/agent/thread
    - Enables cross-chat memory (campaign history across threads)

    Usage:
        memory = MemoryManager(
            tenant_id="org-123",
            agent_id="agent-456",
            agent_traits={"name": "ContentCreator", "type": "workflow"}
        )

        # Store interaction
        await memory.store_interaction(
            role="user",
            content="Create a video about AI trends",
            session_id="thread-789"
        )

        # Retrieve context (Mem0 + Qdrant)
        context = await memory.get_agent_context(
            user_input="What topics should I cover?",
            session_id="thread-789",
            k=5
        )

        # Get campaign history (Qdrant cross-chat)
        campaigns = await memory.get_campaigns_by_tenant(limit=10)
    """

    def __init__(
        self,
        tenant_id: str,
        agent_id: str,
        agent_traits: Optional[Dict[str, Any]] = None,
        collection_name: str = "content_creation_memory"
    ):
        """
        Initialize hybrid Mem0 + Qdrant memory manager.

        Args:
            tenant_id: Organization/tenant identifier
            agent_id: Agent identifier
            agent_traits: Agent configuration (name, traits, etc.)
            collection_name: Qdrant collection name
        """
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.agent_traits = agent_traits or {}
        self.namespace = f"{tenant_id}:{agent_id}"
        self.collection_name = collection_name

        # Initialize Mem0 client (semantic long-term memory)
        try:
            self.mem0_client = Memory(
                api_key=settings.MEM0_API_KEY,
                org_id=settings.MEM0_ORG_ID
            )
            logger.info(f"Mem0 client initialized for namespace: {self.namespace}")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0 client: {e}")
            raise

        # Initialize Qdrant client (conversation history)
        try:
            qdrant_host = getattr(settings, 'QDRANT_HOST', 'localhost')
            qdrant_port = getattr(settings, 'QDRANT_PORT', 6333)

            self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
            self.embedding = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY,
                dimensions=768
            )
            self.embedding_size = 768

            # Ensure collection exists
            self._ensure_collection_exists()

            logger.info(f"Qdrant client initialized: {qdrant_host}:{qdrant_port}")
        except Exception as e:
            logger.warning(f"Qdrant initialization failed: {e}. Continuing with Mem0 only.")
            self.qdrant_client = None
            self.embedding = None

    def _ensure_collection_exists(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        if not self.qdrant_client:
            return

        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_size,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                logger.info(f"Qdrant collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")

    def agent_namespace(self) -> str:
        """Get agent-level memory namespace."""
        return f"{self.tenant_id}:{self.agent_id}"

    def thread_namespace(self, thread_id: str) -> str:
        """Get thread-specific memory namespace."""
        return f"{self.tenant_id}:{self.agent_id}:thread:{thread_id}"

    def user_namespace(self, user_id: str) -> str:
        """Get user-specific memory namespace."""
        return f"{self.tenant_id}:{self.agent_id}:user:{user_id}"

    async def store_interaction(
        self,
        role: str,
        content: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a message in BOTH Mem0 (semantic) and Qdrant (vector).

        Args:
            role: Message role ("user", "assistant", "system")
            content: Message content
            session_id: Thread/session identifier
            metadata: Additional metadata to store
        """
        try:
            # Build metadata
            full_metadata = {
                "role": role,
                "session_id": session_id,
                "tenant_id": self.tenant_id,
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }

            # Store in Mem0 (semantic long-term memory)
            self.mem0_client.add(
                messages=[{"role": role, "content": content}],
                user_id=self.thread_namespace(session_id),
                metadata=full_metadata
            )

            # Store in Qdrant (conversation history vector store)
            if self.qdrant_client and self.embedding:
                await self._store_in_qdrant(
                    content=content,
                    role=role,
                    session_id=session_id,
                    metadata=full_metadata
                )

            logger.debug(
                f"Stored {role} message in Mem0 + Qdrant: {content[:50]}... "
                f"(session: {session_id})"
            )

        except Exception as e:
            logger.error(f"Failed to store interaction: {e}")
            # Don't raise - memory storage should not block workflow

    async def _store_in_qdrant(
        self,
        content: str,
        role: str,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Store conversation in Qdrant vector store.

        Args:
            content: Message content
            role: Message role
            session_id: Thread identifier
            metadata: Full metadata dict
        """
        try:
            # Create document for vector storage
            formatted_content = f"{role.capitalize()}: {content}"
            doc = Document(
                page_content=formatted_content,
                metadata=metadata
            )

            # Add tenant_id to metadata for multi-tenant filtering
            doc.metadata["tenant_id"] = self.tenant_id

            # Store in Qdrant
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding=self.embedding
            )

            await vector_store.aadd_documents([doc])

            logger.debug(f"Stored in Qdrant: thread={session_id}, role={role}")

        except Exception as e:
            logger.error(f"Failed to store in Qdrant: {e}")

    async def get_agent_context(
        self,
        user_input: str,
        session_id: str,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context from BOTH Mem0 and Qdrant.

        This dual-path retrieval provides:
        1. Mem0: Long-term semantic memory (facts, preferences, learnings)
        2. Qdrant: Conversation history from current and past threads

        Args:
            user_input: Current user input (query for semantic search)
            session_id: Thread/session identifier
            k: Number of memories to retrieve from each source

        Returns:
            Dict containing:
                - memories: Combined list of relevant memory contents
                - confidence_score: Average relevance score
                - namespace: Memory namespace used
                - retrieved_memories: Full memory objects with metadata
                - recent_messages: Recent conversation from Qdrant
                - campaign_history: Past campaign data (if available)
        """
        try:
            # Path 1: Search Mem0 for semantic long-term memories
            mem0_results = self.mem0_client.search(
                query=user_input,
                user_id=self.thread_namespace(session_id),
                limit=k
            )

            # Extract Mem0 memories
            memories = []
            retrieved_memories = []
            total_score = 0.0

            for result in mem0_results.get("results", []):
                memory_content = result.get("memory", "")
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})

                memories.append(memory_content)
                retrieved_memories.append({
                    "content": memory_content,
                    "score": score,
                    "source": "mem0",
                    "metadata": metadata
                })
                total_score += score

            # Path 2: Search Qdrant for conversation history
            qdrant_memories = []
            if self.qdrant_client and self.embedding:
                qdrant_memories = await self._search_qdrant(
                    query=user_input,
                    session_id=session_id,
                    k=k
                )
                retrieved_memories.extend(qdrant_memories)

            # Get recent messages from current thread
            recent_messages = await self.get_recent_messages(session_id, limit=10)

            # Calculate average confidence
            confidence_score = total_score / max(len(memories), 1)

            logger.debug(
                f"Retrieved {len(memories)} memories from Mem0, "
                f"{len(qdrant_memories)} from Qdrant "
                f"(confidence: {confidence_score:.2f})"
            )

            return {
                "memories": memories,
                "confidence_score": confidence_score,
                "namespace": self.thread_namespace(session_id),
                "retrieved_memories": retrieved_memories,
                "recent_messages": recent_messages,
                "qdrant_results": qdrant_memories
            }

        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            # Return empty context on failure
            return {
                "memories": [],
                "confidence_score": 0.0,
                "namespace": self.thread_namespace(session_id),
                "retrieved_memories": [],
                "recent_messages": [],
                "qdrant_results": []
            }

    async def _search_qdrant(
        self,
        query: str,
        session_id: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search Qdrant for relevant conversation history.

        Args:
            query: Search query
            session_id: Current thread ID
            k: Number of results

        Returns:
            List of relevant conversation snippets
        """
        try:
            if not self.qdrant_client or not self.embedding:
                return []

            # Create vector store for searching
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding=self.embedding
            )

            # Search with tenant_id filter (multi-tenancy)
            results = await vector_store.asimilarity_search_with_score(
                query=query,
                k=k,
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.tenant_id",
                            match=models.MatchValue(value=self.tenant_id)
                        )
                    ]
                )
            )

            # Format results
            qdrant_memories = []
            for doc, score in results:
                qdrant_memories.append({
                    "content": doc.page_content,
                    "score": score,
                    "source": "qdrant",
                    "metadata": doc.metadata
                })

            return qdrant_memories

        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation messages from Qdrant (if available) or Mem0.

        Priority: Qdrant > Mem0

        Args:
            session_id: Thread/session identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dicts with role, content, timestamp
        """
        try:
            # Try Qdrant first (faster, structured)
            if self.qdrant_client:
                messages = await self._get_messages_from_qdrant(session_id, limit)
                if messages:
                    logger.debug(f"Retrieved {len(messages)} messages from Qdrant")
                    return messages

            # Fallback to Mem0
            results = self.mem0_client.get_all(
                user_id=self.thread_namespace(session_id)
            )

            # Extract and sort by timestamp
            messages = []
            for result in results.get("results", []):
                metadata = result.get("metadata", {})
                if metadata.get("session_id") == session_id:
                    messages.append({
                        "role": metadata.get("role", "unknown"),
                        "content": result.get("memory", ""),
                        "timestamp": metadata.get("timestamp", ""),
                        "metadata": metadata
                    })

            # Sort by timestamp (newest first) and limit
            messages.sort(key=lambda x: x["timestamp"], reverse=True)
            messages = messages[:limit]

            logger.debug(f"Retrieved {len(messages)} recent messages from Mem0")

            return messages

        except Exception as e:
            logger.error(f"Failed to retrieve recent messages: {e}")
            return []

    async def _get_messages_from_qdrant(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a specific thread from Qdrant.

        Args:
            session_id: Thread identifier
            limit: Max messages to retrieve

        Returns:
            List of message dicts
        """
        try:
            if not self.qdrant_client:
                return []

            # Scroll through Qdrant with filters
            response = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.tenant_id",
                            match=models.MatchValue(value=self.tenant_id)
                        ),
                        models.FieldCondition(
                            key="metadata.session_id",
                            match=models.MatchValue(value=session_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            # Extract messages
            messages = []
            for point in response[0]:
                payload = point.payload
                messages.append({
                    "role": payload.get("metadata", {}).get("role", "unknown"),
                    "content": payload.get("page_content", ""),
                    "timestamp": payload.get("metadata", {}).get("timestamp", ""),
                    "metadata": payload.get("metadata", {})
                })

            # Sort by timestamp (oldest first for conversation flow)
            messages.sort(key=lambda x: x["timestamp"])

            return messages

        except Exception as e:
            logger.error(f"Failed to get messages from Qdrant: {e}")
            return []

    async def get_campaigns_by_tenant(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get campaign history across all threads for this tenant.

        This enables cross-chat memory - supervisor can learn from past campaigns.

        Args:
            limit: Max campaigns to retrieve
            offset: Pagination offset

        Returns:
            List of campaign/workflow metadata
        """
        try:
            if not self.qdrant_client:
                logger.warning("Qdrant not available, cannot retrieve campaign history")
                return []

            # Search for all content creation workflows
            response = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.tenant_id",
                            match=models.MatchValue(value=self.tenant_id)
                        ),
                        models.FieldCondition(
                            key="metadata.role",
                            match=models.MatchValue(value="assistant")
                        )
                    ]
                ),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            # Extract campaign data
            campaigns = []
            for point in response[0]:
                payload = point.payload
                metadata = payload.get("metadata", {})

                # Only include workflow results
                if "workflow_id" in metadata or "generated_video_url" in metadata:
                    campaigns.append({
                        "session_id": metadata.get("session_id"),
                        "timestamp": metadata.get("timestamp"),
                        "content": payload.get("page_content", ""),
                        "metadata": metadata
                    })

            # Sort by timestamp (most recent first)
            campaigns.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            logger.info(f"Retrieved {len(campaigns)} campaign records for tenant {self.tenant_id}")

            return campaigns

        except Exception as e:
            logger.error(f"Failed to get campaign history: {e}")
            return []

    async def process_interaction(
        self,
        user_input: str,
        agent_response: str,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Process and store a complete interaction (user + agent).

        This is a convenience method that stores both user and agent messages.

        Args:
            user_input: User's message
            agent_response: Agent's response
            session_id: Thread/session identifier
            user_id: User identifier
            metadata: Additional metadata
        """
        # Store user message
        await self.store_interaction(
            role="user",
            content=user_input,
            session_id=session_id,
            metadata={**metadata, "user_id": user_id} if metadata else {"user_id": user_id}
        )

        # Store agent response
        await self.store_interaction(
            role="assistant",
            content=agent_response,
            session_id=session_id,
            metadata=metadata
        )

        logger.info(f"Processed interaction for session {session_id}")

    async def add_system_memory(
        self,
        content: str,
        memory_type: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add agent-level system memory (not tied to specific session).

        Args:
            content: Memory content
            memory_type: Type of memory (system, fact, preference)
            metadata: Additional metadata
        """
        try:
            full_metadata = {
                "type": memory_type,
                "tenant_id": self.tenant_id,
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }

            self.client.add(
                messages=[{"role": "system", "content": content}],
                user_id=self.agent_namespace(),
                metadata=full_metadata
            )

            logger.info(f"Added system memory: {content[:50]}...")

        except Exception as e:
            logger.error(f"Failed to add system memory: {e}")

    async def clear_session_memory(self, session_id: str) -> None:
        """
        Clear all memories for a specific session.

        Args:
            session_id: Thread/session identifier to clear
        """
        try:
            # Mem0 API for deleting user memories
            self.client.delete_all(
                user_id=self.thread_namespace(session_id)
            )

            logger.info(f"Cleared memory for session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to clear session memory: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics for this agent.

        Returns:
            Dict with memory usage stats
        """
        try:
            # Get all memories for this agent
            results = self.client.get_all(user_id=self.agent_namespace())

            return {
                "namespace": self.namespace,
                "total_memories": len(results.get("results", [])),
                "agent_traits": self.agent_traits
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                "namespace": self.namespace,
                "total_memories": 0,
                "error": str(e)
            }
