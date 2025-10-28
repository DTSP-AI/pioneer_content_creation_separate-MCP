"""
Memory Manager for Content Creation Agent - Mem0-Powered

ARCHITECTURE (Qdrant REMOVED - Mem0 is the sole semantic engine):
1. SHORT-TERM: In-memory thread storage (fast, session-based)
2. LONG-TERM: Mem0 for semantic facts/learnings (NOT raw messages)
3. PERSISTENT: PostgreSQL for structured data (source of truth)

PATTERN COMPLIANCE:
- Mem0-first design: Leverages Mem0's built-in vector store and embeddings
- Single responsibility: Memory operations only
- Namespace isolation: {tenant_id}:{agent_id}
- Thread-based short-term memory
- Composite scoring: Recency + Semantic + Reinforcement (via Mem0)
- NO redundancy: Removed Qdrant entirely

KEY PRINCIPLES:
- PostgreSQL = Source of truth for messages (via database/models.py)
- Mem0 = Complete semantic memory solution (vector store + embeddings + search)
- Thread memory = Global in-memory storage for speed
- NO Qdrant: Mem0 provides all vector capabilities natively

✅ VERIFIED ARCHITECTURE COMPLIANCE (2025-01-20):
- Memory segregation: SHORT-TERM (in-memory) vs LONG-TERM (Mem0) vs PERSISTENT (PostgreSQL)
- No triple-write: Each memory type has distinct responsibility
- Qdrant REMOVED: Mem0 is the single semantic engine
- PostgreSQL priority: All workflow state goes to DB first via models.py
- Mem0 usage: Semantic facts/learnings + automatic embeddings + vector search
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Global thread storage for persistence across requests (blueprint pattern)
_global_threads: Dict[str, List[Dict[str, Any]]] = {}

from backend.config import get_settings
settings = get_settings()

# Mem0 integration - graceful fallback if unavailable
try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("mem0 not available - using local memory only")
    MemoryClient = None


class MemorySettings(BaseModel):
    """Memory configuration following blueprint specification"""
    org_id: str
    project_id: str
    # Retrieval parameters
    k: int = 6
    alpha_recency: float = 0.35
    alpha_semantic: float = 0.45
    alpha_reinforcement: float = 0.20
    decay_halflife_hours: float = 24.0


class MemoryManager:
    """
    Single API for thread, persistent & learning memory.

    Based on ExampleRepoREADONLY/backend/memory/memory_manager.py blueprint.

    USAGE:
        # Create memory manager
        memory = MemoryManager(tenant_id="org-123", agent_id="agent-456")

        # Short-term: Thread storage (in-memory)
        memory.append_thread("session-789", "user", "Create a TikTok video")
        memory.append_thread("session-789", "assistant", "Sure! What topic?")

        # Get recent context
        context = memory.get_thread_context("session-789")

        # Long-term: Store insights (NOT raw messages)
        memory.add_fact("user-123", "User prefers short-form vertical videos")

        # Retrieve relevant memories with composite scoring
        memories = memory.retrieve("user-123", "What video style does user like?")

        # Reinforce important memories
        memory.reinforce(memory_id="mem_xyz", delta=1.0)
    """

    def __init__(self, tenant_id: str, agent_id: str):
        """
        Initialize memory manager with Mem0 semantic engine.

        Args:
            tenant_id: Organization/tenant identifier
            agent_id: Agent identifier
        """
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.namespace = f"{tenant_id}:{agent_id}"

        # Initialize settings
        self.settings = MemorySettings(
            org_id=tenant_id,
            project_id=agent_id
        )

        # Initialize Mem0 client (semantic memory engine with built-in vector store)
        mem0_api_key = getattr(settings, 'MEM0_API_KEY', None)
        mem0_org_id = getattr(settings, 'MEM0_ORG_ID', None)

        if MEM0_AVAILABLE:
            try:
                # Mem0 Cloud (production) - requires API key
                if mem0_api_key and mem0_api_key.startswith('m0-'):
                    self.mem0 = MemoryClient(
                        api_key=mem0_api_key,
                        org_id=mem0_org_id or self.settings.org_id,
                        project_id=self.settings.project_id
                    )
                    logger.info(
                        f"✅ Mem0 Cloud initialized: "
                        f"namespace={self.namespace}, "
                        f"org_id={mem0_org_id or self.settings.org_id}"
                    )
                # Mem0 Local (development) - uses local vector store
                else:
                    self.mem0 = MemoryClient()
                    logger.info(
                        f"✅ Mem0 Local initialized: "
                        f"namespace={self.namespace}, "
                        f"mode=local (built-in embeddings + Qdrant embedded)"
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize Mem0: {e}. Memory features will be limited.")
                self.mem0 = None
        else:
            logger.warning("Mem0 not available - install with: pip install mem0ai>=0.1.32")
            self.mem0 = None

    # ============================================================================
    # SHORT-TERM MEMORY (Thread-based, in-memory)
    # ============================================================================

    def append_thread(self, session_id: str, role: str, content: str):
        """
        Add message to short-term thread memory (in-memory).

        This is the PRIMARY method for storing conversation messages.
        Messages are kept in memory for fast access and automatically
        bounded to the last 20 messages.

        Args:
            session_id: Thread/session identifier
            role: Message role ("user", "assistant", "system")
            content: Message content
        """
        global _global_threads
        _global_threads.setdefault(session_id, []).append({
            "role": role,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat()
        })
        # Bound window size to prevent memory bloat
        _global_threads[session_id] = _global_threads[session_id][-20:]

        logger.debug(f"Added {role} message to thread {session_id}: {content[:50]}...")

    def get_thread_context(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get recent conversation context from thread.

        Returns last 20 messages from the thread (bounded by append_thread).

        Args:
            session_id: Thread/session identifier

        Returns:
            List of message dicts with role, content, timestamp (copy, not reference)
        """
        global _global_threads
        # Return a copy to prevent external modifications to internal state
        return list(_global_threads.get(session_id, []))

    def get_thread_history(self, session_id: str = "default_session") -> List:
        """
        Get thread history as LangChain messages for compatibility.

        Args:
            session_id: Thread/session identifier

        Returns:
            List of LangChain HumanMessage/AIMessage objects
        """
        from langchain_core.messages import HumanMessage, AIMessage

        thread_data = self.get_thread_context(session_id)
        messages = []

        for item in thread_data:
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            elif item["role"] == "assistant":
                messages.append(AIMessage(content=item["content"]))

        return messages

    # ============================================================================
    # LONG-TERM MEMORY (Mem0 - semantic facts/learnings)
    # ============================================================================

    def add_fact(
        self,
        user_id: str,
        text: str,
        score: Optional[float] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Store a semantic fact/learning in long-term memory (Mem0).

        Mem0 automatically:
        - Generates embeddings for semantic search
        - Stores in built-in vector store
        - Handles deduplication and conflict resolution
        - Maintains temporal context

        Use this for:
        - User preferences: "User prefers vertical videos"
        - Agent learnings: "Best posting time is 6pm"
        - Campaign insights: "Viral topics: AI, productivity"
        - Workflow outcomes: "TikTok campaign succeeded, cost $2.50"

        Do NOT use this for raw conversation messages - use append_thread() instead.

        Args:
            user_id: User identifier
            text: Semantic fact/learning to store
            score: Optional reinforcement score (positive=success, negative=failure)
            category: Optional category (e.g., "preference", "outcome", "insight")
            tags: Optional tags for filtering (e.g., ["tiktok", "viral", "trending"])

        Returns:
            Memory ID if successful, empty string otherwise
        """
        if not self.mem0:
            logger.warning("Mem0 not available, fact not persisted")
            return ""

        # Build enhanced metadata
        meta = {}
        if score is not None:
            meta["rl_reward"] = score
        if category:
            meta["category"] = category
        if tags:
            meta["tags"] = tags

        try:
            res = self.mem0.add(
                [{"role": "user", "content": text}],
                user_id=user_id,
                metadata=meta if meta else None
            )
            mem_id = res["id"] if isinstance(res, dict) and "id" in res else ""
            logger.info(
                f"✅ Mem0 stored: {text[:50]}... "
                f"(ID: {mem_id}, category: {category}, tags: {tags})"
            )
            return mem_id
        except Exception as e:
            logger.error(f"Failed to add fact to Mem0: {e}")
            return ""

    def reinforce(self, memory_id: str, delta: float):
        """
        Adjust reinforcement score on a memory (±).

        Use this to strengthen or weaken memories based on feedback:
        - Positive delta: Memory was helpful (+1.0)
        - Negative delta: Memory was not relevant (-0.5)

        Args:
            memory_id: Memory ID to reinforce
            delta: Score adjustment (positive or negative)
        """
        if not self.mem0:
            return

        try:
            self.mem0.add_history(
                memory_id=memory_id,
                event={"type": "reinforce", "delta": delta}
            )
            logger.debug(f"Reinforced memory {memory_id} with delta {delta}")
        except Exception as e:
            logger.error(f"Failed to reinforce memory {memory_id}: {e}")

    def retrieve(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories with composite scoring.

        Combines:
        - Semantic similarity (45%)
        - Recency / time decay (35%)
        - Reinforcement feedback (20%)

        Args:
            user_id: User identifier
            query: Search query

        Returns:
            List of top-K memories with composite scores
        """
        if not self.mem0:
            return []

        try:
            raw = self.mem0.search(
                query=query,
                user_id=user_id,
                k=self.settings.k
            )
            return self._rank_with_composite(raw)
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []

    def _rank_with_composite(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply composite scoring: semantic + recency + reinforcement + identity.

        Formula:
            score = (0.40 * semantic) + (0.30 * recency) + (0.20 * reinforcement) + (0.10 * identity)

        Identity boost: Memories aligned with agent's mission get higher relevance.
        Example: Supervisor agent (content strategist) → boost content/social media memories

        Args:
            items: Raw Mem0 search results

        Returns:
            Re-ranked results with composite scores
        """
        if not items:
            return []

        # Get agent identity keywords for filtering
        agent_identity_keywords = self._get_agent_identity_keywords()

        now = datetime.now(timezone.utc)
        out = []

        for it in items:
            # Semantic similarity from Mem0
            sem = float(it.get("score", 0.0))

            # Time decay (exponential)
            created = it.get("created_at")
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00")) if isinstance(created, str) else now
            except Exception:
                ts = now

            hours = max(0.0, (now - ts).total_seconds() / 3600.0)
            lam = 0.693147 / max(1e-6, self.settings.decay_halflife_hours)  # ln(2)/half-life
            recency = pow(2.718281828, -lam * hours)

            # Reinforcement history
            r_hist = self.mem0.history(memory_id=it["id"]) if self.mem0 else []
            r_total = 0.0
            for ev in r_hist or []:
                if (ev.get("event", {}) or {}).get("type") == "reinforce":
                    r_total += float(ev["event"].get("delta", 0.0))

            # Identity relevance (NEW: agent-specific memory filtering)
            identity_score = self._calculate_identity_relevance(
                it.get("memory", "") or it.get("text", ""),
                agent_identity_keywords
            )

            # Composite score with identity boost
            composite = (
                0.40 * sem +            # Semantic similarity (40%)
                0.30 * recency +        # Recency / time decay (30%)
                0.20 * r_total +        # Reinforcement feedback (20%)
                0.10 * identity_score   # Identity alignment (10%)
            )
            it["composite"] = composite
            it["identity_boost"] = identity_score
            out.append(it)

        # Sort by composite score
        out.sort(key=lambda x: x["composite"], reverse=True)
        return out[:self.settings.k]

    # ============================================================================
    # REFLECTION & INSIGHTS
    # ============================================================================

    def reflect(self, user_id: str, session_id: str, outcome: str) -> str:
        """
        Create a distilled reflection from conversation and persist as fact.

        Use this at the end of a session to extract learnings:
        - "Campaign successful: vertical format + trending audio"
        - "User responded well to concise scripts"

        Args:
            user_id: User identifier
            session_id: Thread/session to reflect on
            outcome: Session outcome or result

        Returns:
            Memory ID of stored reflection
        """
        # Get recent context
        window = self.get_thread_context(session_id)[-6:]

        # Create reflection summary
        user_cues = '; '.join(m['content'] for m in window if m['role'] == 'user')
        note = f"Reflection: outcome={outcome}; user_requests={user_cues}"

        # Store as fact
        return self.add_fact(user_id, f"[reflection] {note}")

    # ============================================================================
    # LEGACY COMPATIBILITY (for existing code)
    # ============================================================================

    def add_message(self, role: str, content: str):
        """Legacy API compatibility - uses default session"""
        self.append_thread("default_session", role, content)

    def get_context(self, query: str):
        """Legacy API compatibility"""
        recent = self.get_thread_context("default_session")[-5:]
        relevant = self.retrieve(user_id="default_user", query=query)
        return {"recent": recent, "relevant": relevant}

    def append_human(self, text: str):
        """Backward compatibility wrapper"""
        self.append_thread("default_session", "user", text)

    def append_ai(self, text: str):
        """Backward compatibility wrapper"""
        self.append_thread("default_session", "assistant", text)

    def get_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
        global _global_threads
        return {
            "namespace": self.namespace,
            "org_id": self.settings.org_id,
            "project_id": self.settings.project_id,
            "thread_count": len(_global_threads),
            "mem0_enabled": self.mem0 is not None
        }

    # ============================================================================
    # IDENTITY-BASED MEMORY FILTERING (Agent Contract Standard)
    # ============================================================================

    def _get_agent_identity_keywords(self) -> List[str]:
        """
        Get agent-specific keywords for memory filtering.

        For supervisor_agent (content strategist):
        - Mission: content strategy, social media, viral, engagement, platforms
        - Role: orchestrator, strategist, advisor
        """
        # Map agent_id to mission keywords
        identity_keywords_map = {
            "supervisor": [
                "content", "video", "tiktok", "youtube", "shorts", "social", "media",
                "viral", "trending", "campaign", "platform", "engagement", "strategy",
                "creator", "audience", "hook", "caption", "hashtag", "views"
            ],
            "content_creation": [
                "script", "voiceover", "captions", "video", "generation", "piapi",
                "model", "quality", "visual", "audio", "editing"
            ]
        }

        # Extract base agent_id (remove suffix like "_agent")
        base_id = self.agent_id.replace("_agent", "")

        keywords = identity_keywords_map.get(base_id, [])
        logger.debug(f"Agent '{self.agent_id}' identity keywords: {keywords[:5]}...")

        return keywords

    def _calculate_identity_relevance(
        self,
        memory_text: str,
        identity_keywords: List[str]
    ) -> float:
        """
        Calculate how relevant a memory is to agent's identity/mission.

        Memories aligned with agent mission get higher scores.
        Example: Supervisor agent boosts memories about "tiktok campaign" or "viral content"

        Args:
            memory_text: Memory content to evaluate
            identity_keywords: Agent's mission/role keywords

        Returns:
            Identity relevance score (0.0-1.0)
        """
        if not memory_text or not identity_keywords:
            return 0.0

        memory_lower = memory_text.lower()

        # Count keyword matches
        matches = sum(1 for keyword in identity_keywords if keyword in memory_lower)

        # Score: 0.1 per match, capped at 1.0
        score = min(1.0, matches * 0.1)

        if score > 0.3:
            logger.debug(f"High identity relevance ({score:.2f}) - matched {matches} keywords")

        return score

    # ============================================================================
    # ASYNC WRAPPERS (for LangGraph integration)
    # ============================================================================

    async def store_interaction(
        self,
        role: str,
        content: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Async wrapper for storing messages.

        NOTE: This now ONLY stores in thread memory (in-memory).
        PostgreSQL persistence should be handled by the database layer,
        NOT by the memory manager.

        Args:
            role: Message role
            content: Message content
            session_id: Thread identifier
            metadata: Optional metadata (ignored - use PostgreSQL models instead)
        """
        self.append_thread(session_id, role, content)

    async def get_agent_context(
        self,
        user_input: str,
        session_id: str,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context (thread + semantic memories).

        Args:
            user_input: Current user input
            session_id: Thread identifier
            k: Number of memories to retrieve

        Returns:
            Dict with recent_messages and relevant memories
        """
        # Get recent thread context
        recent = self.get_thread_context(session_id)

        # Get relevant semantic memories
        memories = self.retrieve(user_id=session_id, query=user_input)

        return {
            "recent_messages": recent,
            "memories": [m.get("memory", "") for m in memories],
            "retrieved_memories": memories,
            "confidence_score": memories[0].get("composite", 0.0) if memories else 0.0,
            "namespace": self.namespace
        }


# ============================================================================
# LANGGRAPH NODES (for graph integration)
# ============================================================================

async def memory_retrieval_node(state):
    """Memory retrieval node for LangGraph"""
    session_id = state.get("session_id", "default")
    tenant_id = state.get("tenant_id", "default")
    agent_id = state.get("agent_id", "default")

    memory_manager = MemoryManager(tenant_id, agent_id)
    current_message = state.get("current_message", "")

    if current_message:
        context = await memory_manager.get_agent_context(current_message, session_id)
        state["short_term_context"] = str(context["recent_messages"])
        state["persistent_context"] = str(context["memories"])

    return state


async def memory_storage_node(state):
    """Memory storage node for LangGraph"""
    session_id = state.get("session_id", "default")
    tenant_id = state.get("tenant_id", "default")
    agent_id = state.get("agent_id", "default")

    memory_manager = MemoryManager(tenant_id, agent_id)

    # Store user message
    user_input = state.get("current_message", "")
    if user_input:
        memory_manager.add_message("user", user_input)

    # Store agent response
    agent_response = state.get("agent_response", "")
    if agent_response:
        memory_manager.add_message("assistant", agent_response)

    return state
