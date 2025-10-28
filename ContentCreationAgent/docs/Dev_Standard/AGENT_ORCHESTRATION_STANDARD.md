# AGENT ORCHESTRATION STANDARD

**Project:** Universal AI Agent Systems with LangGraph/LangChain
**Purpose:** Define the immutable law for agent orchestration, state management, memory integration, and tool execution
**Based On:** AGENT_CREATION_STANDARD.md + STACK_1ST_PRINCIPLES_GUARDRAIL.md + LangChain/LangGraph Knowledge Base
**Last Updated:** 2025-01-15

---

## TABLE OF CONTENTS

1. [Philosophy & Core Principles](#philosophy--core-principles)
2. [Technology Stack - The Law](#technology-stack---the-law)
3. [LangGraph Workflow Architecture](#langgraph-workflow-architecture)
4. [Agent State Management](#agent-state-management)
5. [Memory Integration Patterns](#memory-integration-patterns)
6. [Tool Execution Framework](#tool-execution-framework)
7. [Multi-Agent Orchestration](#multi-agent-orchestration)
8. [Node Implementation Patterns](#node-implementation-patterns)
9. [Error Handling & Resilience](#error-handling--resilience)
10. [Testing & Validation](#testing--validation)
11. [Production Deployment Patterns](#production-deployment-patterns)
12. [Reference Implementation](#reference-implementation)

---

## PHILOSOPHY & CORE PRINCIPLES

### The Orchestration Trinity

```
JSON Contract (WHAT) → LangGraph Workflow (HOW) → Memory + Tools (WHERE)
        ↓                        ↓                          ↓
   Agent Identity         State Transitions          Context & Actions
```

### Core Tenets

#### 1. LangGraph is the ONLY Orchestrator
- **NO custom state machines** - Use LangGraph StateGraph exclusively
- **NO manual conversation loops** - Let LangGraph manage flow
- **NO imperative orchestration** - Declare workflows as graphs
- All agent behavior flows through LangGraph nodes and edges

#### 2. State as Single Source of Truth
- State is a typed dictionary (TypedDict)
- Nodes read from and write to state
- NO side effects outside state updates
- State persists via LangGraph checkpointers

#### 3. Memory is Namespace-Isolated
- Mem0 for persistent semantic memory
- PostgreSQL for structured thread history
- Namespace pattern: `{tenant_id}:{agent_id}:thread:{thread_id}`
- NO local vector stores (FAISS, Chroma, Qdrant)

#### 4. Tools are LangChain-Compatible
- All tools extend LangChain BaseTool
- Tools are bound to LLMs, not agents
- Tool execution happens within LangGraph nodes
- NO custom tool orchestration

#### 5. Agents are Node Functions
- Each agent is a set of node functions
- Agents delegate to sub-agents via graph composition
- Hierarchical orchestration through nested StateGraphs
- NO custom agent classes outside LangGraph patterns

---

## TECHNOLOGY STACK - THE LAW

### Orchestration Layer (NON-NEGOTIABLE)

```python
# REQUIRED VERSIONS
langgraph==0.2.27+  # State machine, multi-agent workflows
langchain==0.3.23+  # Tool integration, chains, agents
langchain-openai   # LLM provider (or langchain-anthropic)
```

**Rules:**
- All workflows MUST use `StateGraph` from LangGraph
- All tools MUST be LangChain-compatible (`BaseTool` or `@tool` decorator)
- NO Crew AI, AutoGen, or custom orchestration frameworks
- NO manual conversation loops or state machines

### Memory & Database Layer

```python
# REQUIRED
mem0==0.1.17+           # Cloud semantic memory
asyncpg                 # PostgreSQL async driver
supabase                # Database + auth + RLS
```

**Rules:**
- Mem0 MUST be used for all semantic memory operations
- PostgreSQL MUST be used for structured data (threads, messages, agents)
- Supabase RLS MUST enforce multi-tenancy
- NO Redis (deprecated), NO local vector stores

### Voice & Real-Time Layer (Optional)

```python
# REQUIRED for voice agents
livekit==1.0.12+        # WebRTC rooms, real-time streaming
deepgram==3.7.0+        # Speech-to-Text
elevenlabs==1.8.0+      # Text-to-Speech
```

**Rules:**
- LiveKit MUST handle all WebRTC and voice streaming
- Deepgram MUST handle STT (speech-to-text)
- ElevenLabs MUST handle TTS (text-to-speech)
- NO direct WebRTC without LiveKit, NO custom audio processing

### LLM Providers

```python
# PRIMARY OPTIONS
openai                  # GPT-4o, GPT-4o-mini
anthropic               # Claude 3.5 Sonnet, Opus
langchain-xai           # Grok models (xAI)
```

**Rules:**
- LLMs MUST be instantiated via LangChain wrappers
- Tool binding MUST use `.bind_tools()` method
- Structured output MUST use `.with_structured_output()`
- NO direct API calls outside LangChain abstractions

---

## LANGGRAPH WORKFLOW ARCHITECTURE

### Standard Agent Workflow Pattern

Every agent follows this canonical 5-node workflow:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any, List

class AgentState(TypedDict):
    """Standard agent state schema"""
    # Input
    agent_id: str
    tenant_id: str
    user_id: str
    thread_id: str
    input_text: str

    # Agent configuration
    agent_contract: Dict[str, Any]
    system_prompt: str

    # Memory context
    memory_context: Dict[str, Any]
    retrieved_memories: List[Dict[str, Any]]
    recent_messages: List[Dict[str, Any]]

    # Processing
    llm_response: str
    response_text: str
    workflow_status: str

    # Optional: Tool execution
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]

    # Optional: Cognitive triggers
    cognitive_triggers: List[str]
    trigger_fired: bool

    # Metadata
    traits: Dict[str, int]
    configuration: Dict[str, Any]


def build_agent_workflow() -> StateGraph:
    """
    Standard agent workflow with 5 nodes:
    1. retrieve_context - Get memory from Mem0
    2. build_prompt - Construct system prompt + user input
    3. invoke_llm - Call LLM with tools
    4. post_process - Format and validate response
    5. check_triggers - Check cognitive triggers/interventions
    """
    workflow = StateGraph(AgentState)

    # Define nodes
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("build_prompt", build_prompt_node)
    workflow.add_node("invoke_llm", invoke_llm_node)
    workflow.add_node("post_process", post_process_node)
    workflow.add_node("check_triggers", check_triggers_node)

    # Define edges (linear flow)
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "build_prompt")
    workflow.add_edge("build_prompt", "invoke_llm")
    workflow.add_edge("invoke_llm", "post_process")
    workflow.add_edge("post_process", "check_triggers")
    workflow.add_edge("check_triggers", END)

    return workflow.compile()
```

### Node Implementation Rules

#### Node Function Signature

```python
async def node_function(state: AgentState) -> Dict[str, Any]:
    """
    Standard node function pattern

    Args:
        state: Current agent state (read-only dict)

    Returns:
        Dict with state updates (merged into state)
    """
    # 1. Read from state
    user_input = state["input_text"]
    agent_id = state["agent_id"]

    # 2. Perform operation
    result = await some_operation(user_input, agent_id)

    # 3. Return state updates
    return {
        "some_field": result,
        "workflow_status": "operation_complete"
    }
```

**Rules:**
- Nodes MUST be async functions
- Nodes MUST return Dict[str, Any] for state updates
- Nodes MUST NOT mutate state directly
- Nodes MUST handle errors gracefully
- Nodes SHOULD be pure functions (no hidden side effects)

---

## AGENT STATE MANAGEMENT

### State Schema Design

#### Minimal State Schema

```python
from typing import TypedDict, Dict, Any

class MinimalAgentState(TypedDict):
    """Minimal viable agent state"""
    # Identity
    agent_id: str
    user_id: str
    thread_id: str

    # Input/Output
    input_text: str
    response_text: str

    # Status
    workflow_status: str
```

#### Extended State Schema (Production)

```python
from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime

class ProductionAgentState(TypedDict, total=False):
    """Production-grade agent state with all fields"""

    # === IDENTITY (required) ===
    agent_id: str
    tenant_id: str
    user_id: str
    thread_id: str

    # === INPUT/OUTPUT (required) ===
    input_text: str
    response_text: str

    # === AGENT CONFIGURATION ===
    agent_contract: Dict[str, Any]
    system_prompt: str
    traits: Dict[str, int]
    configuration: Dict[str, Any]

    # === MEMORY CONTEXT ===
    memory_context: Dict[str, Any]
    retrieved_memories: List[Dict[str, Any]]
    recent_messages: List[Dict[str, Any]]

    # === LLM INTERACTION ===
    llm_messages: List[Dict[str, str]]
    llm_response: str
    llm_tokens_used: int
    llm_model: str

    # === TOOL EXECUTION ===
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    tool_errors: List[str]

    # === COGNITIVE TRIGGERS ===
    cognitive_triggers: List[str]
    trigger_fired: bool
    intervention_prompts: List[str]

    # === WORKFLOW CONTROL ===
    workflow_status: str
    current_node: str
    error_message: Optional[str]
    retry_count: int

    # === METADATA ===
    timestamp: str
    session_metadata: Dict[str, Any]
```

### State Update Patterns

#### Partial State Updates

```python
async def update_memory_context(state: AgentState) -> Dict[str, Any]:
    """Update only memory-related fields"""
    memories = await get_memories(state["thread_id"])

    return {
        "retrieved_memories": memories,
        "memory_context": {"confidence": 0.85},
        "workflow_status": "memory_retrieved"
    }
```

#### Additive State Updates

```python
async def add_tool_result(state: AgentState) -> Dict[str, Any]:
    """Add to existing list without replacing"""
    existing_results = state.get("tool_results", [])
    new_result = await execute_tool(state["tool_calls"][0])

    return {
        "tool_results": existing_results + [new_result],
        "workflow_status": "tool_executed"
    }
```

#### Conditional State Updates

```python
async def check_and_update(state: AgentState) -> Dict[str, Any]:
    """Conditional updates based on state"""
    if state.get("trigger_fired"):
        return {
            "response_text": "Intervention triggered",
            "workflow_status": "intervention_active"
        }

    return {
        "workflow_status": "no_intervention"
    }
```

---

## MEMORY INTEGRATION PATTERNS

### Mem0 Memory Manager Integration

#### Memory Manager Initialization

```python
from memoryManager.memory_manager import MemoryManager

async def initialize_memory(
    tenant_id: str,
    agent_id: str,
    agent_traits: Dict[str, Any]
) -> MemoryManager:
    """Initialize Mem0-based memory manager"""
    memory = MemoryManager(
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_traits=agent_traits
    )

    # Add system initialization memory
    await memory.add_memory(
        content=f"Agent initialized",
        memory_type="system",
        metadata={"event": "initialization"}
    )

    return memory
```

#### Memory Retrieval in LangGraph Node

```python
async def retrieve_context_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Retrieve memory context from Mem0

    This node:
    1. Initializes MemoryManager
    2. Retrieves semantic memories from Mem0
    3. Fetches recent thread messages from PostgreSQL
    4. Returns enriched memory context
    """
    try:
        # Initialize memory manager
        memory = MemoryManager(
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            agent_traits=state.get("traits", {})
        )

        # Get memory context (Mem0 + recent messages)
        context = await memory.get_agent_context(
            user_input=state["input_text"],
            session_id=state["thread_id"],
            k=5
        )

        return {
            "memory_context": {
                "namespace": context.namespace,
                "confidence_score": context.confidence_score
            },
            "retrieved_memories": context.retrieved_memories,
            "recent_messages": context.recent_messages,
            "workflow_status": "context_retrieved"
        }

    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        return {
            "retrieved_memories": [],
            "recent_messages": [],
            "workflow_status": "memory_retrieval_failed",
            "error_message": str(e)
        }
```

#### Memory Storage After LLM Response

```python
async def store_interaction_node(state: AgentState) -> Dict[str, Any]:
    """
    Final node: Store interaction in Mem0 and PostgreSQL
    """
    memory = MemoryManager(
        tenant_id=state["tenant_id"],
        agent_id=state["agent_id"],
        agent_traits=state.get("traits", {})
    )

    # Store in Mem0 for semantic search
    await memory.process_interaction(
        user_input=state["input_text"],
        agent_response=state["response_text"],
        session_id=state["thread_id"],
        user_id=state["user_id"]
    )

    # Store in PostgreSQL for thread history
    from database import get_pg_pool
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO thread_messages (thread_id, role, content, created_at)
            VALUES ($1::uuid, $2, $3, NOW())
        """, state["thread_id"], "user", state["input_text"])

        await conn.execute("""
            INSERT INTO thread_messages (thread_id, role, content, created_at)
            VALUES ($1::uuid, $2, $3, NOW())
        """, state["thread_id"], "assistant", state["response_text"])

    return {
        "workflow_status": "interaction_stored"
    }
```

### Memory Namespace Patterns

#### Agent-Level Memory

```python
# Namespace: {tenant_id}:{agent_id}
namespace = memory.agent_namespace()

await memory.add_memory(
    content="Agent-level persistent fact",
    namespace=namespace,
    memory_type="fact"
)
```

#### Thread-Level Memory

```python
# Namespace: {tenant_id}:{agent_id}:thread:{thread_id}
namespace = memory.thread_namespace(thread_id)

await memory.store_interaction(
    role="user",
    content=user_message,
    session_id=thread_id
)
```

#### User-Level Memory

```python
# Namespace: {tenant_id}:{agent_id}:user:{user_id}
namespace = memory.user_namespace(user_id)

await memory.add_memory(
    content="User preference: prefers concise responses",
    namespace=namespace,
    user_id=user_id,
    memory_type="preference"
)
```

---

## TOOL EXECUTION FRAMEWORK

### LangChain Tool Definition

#### Basic Tool Definition

```python
from langchain.tools import BaseTool, tool
from typing import Optional, Type
from pydantic import BaseModel, Field

# METHOD 1: @tool decorator (simple)
@tool
def search_web(query: str) -> str:
    """Search the web for information"""
    # Implementation
    return f"Search results for: {query}"

# METHOD 2: BaseTool subclass (advanced)
class SearchInput(BaseModel):
    """Input schema for search tool"""
    query: str = Field(description="Search query text")
    limit: int = Field(default=5, description="Number of results")

class WebSearchTool(BaseTool):
    """Web search tool with structured input"""
    name = "web_search"
    description = "Search the web for information about a topic"
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, limit: int = 5) -> str:
        """Synchronous execution"""
        # Implementation
        return f"Found {limit} results for: {query}"

    async def _arun(self, query: str, limit: int = 5) -> str:
        """Async execution (preferred)"""
        # Async implementation
        return f"Found {limit} results for: {query}"
```

#### Tool Binding to LLM

```python
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get weather for a location"""
    return f"Weather in {location}: 72°F, sunny"

@tool
def search_database(query: str) -> str:
    """Search internal database"""
    return f"Database results for: {query}"

# Bind tools to LLM
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools([get_weather, search_database])
```

### Tool Execution in LangGraph

#### Method 1: Tool Node with Automatic Execution

```python
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

# Define tools
tools = [get_weather, search_database]

# Create LLM with tools
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

# Create tool execution node
tool_node = ToolNode(tools)

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("llm", lambda state: call_llm(state, llm_with_tools))
workflow.add_node("tools", tool_node)

# Conditional routing
def should_use_tools(state: AgentState) -> str:
    """Check if LLM called tools"""
    last_message = state["llm_messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges("llm", should_use_tools, {
    "tools": "tools",
    END: END
})
workflow.add_edge("tools", "llm")  # Loop back to LLM after tools
```

#### Method 2: Custom Tool Execution Node

```python
async def execute_tools_node(state: AgentState) -> Dict[str, Any]:
    """
    Custom tool execution with error handling
    """
    tool_calls = state.get("tool_calls", [])
    tool_results = []
    tool_errors = []

    for tool_call in tool_calls:
        try:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Execute tool
            if tool_name == "get_weather":
                result = await get_weather(**tool_args)
            elif tool_name == "search_database":
                result = await search_database(**tool_args)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            tool_results.append({
                "tool_name": tool_name,
                "result": result,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            tool_errors.append(str(e))
            tool_results.append({
                "tool_name": tool_call.get("name", "unknown"),
                "error": str(e),
                "status": "failed"
            })

    return {
        "tool_results": tool_results,
        "tool_errors": tool_errors,
        "workflow_status": "tools_executed"
    }
```

### ReAct Agent Pattern (Recommended)

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# Define tools
tools = [get_weather, search_database, calculate]

# Create ReAct agent (automatic tool use + reasoning)
llm = ChatOpenAI(model="gpt-4o-mini")
agent = create_react_agent(llm, tools)

# Use in graph
workflow = StateGraph(AgentState)
workflow.add_node("react_agent", lambda state: agent.invoke({
    "messages": state["llm_messages"]
}))
workflow.set_entry_point("react_agent")
workflow.add_edge("react_agent", END)

graph = workflow.compile()
```

---

## MULTI-AGENT ORCHESTRATION

### Hierarchical Agent Architecture

```
Top-Level Supervisor (Router)
    ├── Research Team Subgraph
    │   ├── Web Search Agent
    │   ├── Database Query Agent
    │   └── Summary Agent
    ├── Content Generation Team Subgraph
    │   ├── Writer Agent
    │   ├── Editor Agent
    │   └── Reviewer Agent
    └── Execution Team Subgraph
        ├── Task Planner Agent
        ├── Code Generator Agent
        └── Validator Agent
```

### Implementation: Nested StateGraphs

#### Step 1: Define Shared State Schema

```python
from typing import TypedDict, List, Dict, Any

class SupervisorState(TypedDict):
    """Top-level supervisor state"""
    user_request: str
    current_team: str
    team_results: Dict[str, Any]
    final_output: str
    workflow_status: str

class TeamState(TypedDict):
    """Subgraph team state (inherits from supervisor)"""
    user_request: str  # From supervisor
    team_task: str
    worker_results: List[Dict[str, Any]]
    team_output: str
    workflow_status: str
```

#### Step 2: Create Worker Agents

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

def create_worker_agent(name: str, tools: List):
    """Create a worker agent with tools"""
    llm = ChatOpenAI(model="gpt-4o-mini")
    system_prompt = f"You are {name}. Your job is to use tools to help with the task."

    return create_react_agent(
        llm,
        tools,
        state_modifier=system_prompt
    )

# Create workers
web_search_agent = create_worker_agent("Web Searcher", [web_search_tool])
database_agent = create_worker_agent("Database Analyst", [db_query_tool])
writer_agent = create_worker_agent("Content Writer", [generate_text_tool])
```

#### Step 3: Create Team Subgraphs

```python
from langgraph.graph import StateGraph, END

def create_research_team() -> StateGraph:
    """Research team subgraph with supervisor"""
    workflow = StateGraph(TeamState)

    # Add worker nodes
    workflow.add_node("web_search", web_search_agent)
    workflow.add_node("database_query", database_agent)
    workflow.add_node("summarize", summarize_results)

    # Add team supervisor
    async def research_supervisor(state: TeamState) -> str:
        """Decide which worker to use next"""
        llm = ChatOpenAI(model="gpt-4o")
        prompt = f"""
        Given task: {state['team_task']}
        Current results: {state['worker_results']}

        Which worker should execute next?
        Options: web_search, database_query, summarize, FINISH
        """
        response = await llm.ainvoke(prompt)
        return response.content.strip()

    workflow.add_conditional_edges(
        "supervisor",
        research_supervisor,
        {
            "web_search": "web_search",
            "database_query": "database_query",
            "summarize": "summarize",
            "FINISH": END
        }
    )

    # All workers report back to supervisor
    workflow.add_edge("web_search", "supervisor")
    workflow.add_edge("database_query", "supervisor")
    workflow.add_edge("summarize", END)

    workflow.set_entry_point("supervisor")

    return workflow.compile()
```

#### Step 4: Create Top-Level Supervisor

```python
def create_supervisor_graph() -> StateGraph:
    """Top-level supervisor routing to team subgraphs"""
    workflow = StateGraph(SupervisorState)

    # Add team subgraphs as nodes
    workflow.add_node("research_team", create_research_team())
    workflow.add_node("content_team", create_content_generation_team())
    workflow.add_node("execution_team", create_execution_team())

    # Top-level supervisor routing
    async def top_supervisor(state: SupervisorState) -> str:
        """Route user request to appropriate team"""
        llm = ChatOpenAI(model="gpt-4o")
        prompt = f"""
        User request: {state['user_request']}

        Which team should handle this?
        Options: research_team, content_team, execution_team, FINISH
        """
        response = await llm.ainvoke(prompt)
        return response.content.strip()

    workflow.add_conditional_edges(
        "supervisor",
        top_supervisor,
        {
            "research_team": "research_team",
            "content_team": "content_team",
            "execution_team": "execution_team",
            "FINISH": END
        }
    )

    # Teams report back to supervisor
    workflow.add_edge("research_team", "supervisor")
    workflow.add_edge("content_team", "supervisor")
    workflow.add_edge("execution_team", "supervisor")

    workflow.set_entry_point("supervisor")

    return workflow.compile()
```

### Agent Communication Patterns

#### Pattern 1: Sequential Handoff

```python
# Agent A → Agent B → Agent C
workflow.add_edge("agent_a", "agent_b")
workflow.add_edge("agent_b", "agent_c")
workflow.add_edge("agent_c", END)
```

#### Pattern 2: Conditional Routing

```python
def router(state: AgentState) -> str:
    """Route based on state conditions"""
    if state["complexity"] > 0.8:
        return "expert_agent"
    return "basic_agent"

workflow.add_conditional_edges(
    "router",
    router,
    {
        "expert_agent": "expert_agent",
        "basic_agent": "basic_agent"
    }
)
```

#### Pattern 3: Parallel Execution

```python
from langgraph.graph import START

# Multiple agents execute in parallel
workflow.add_edge(START, ["agent_a", "agent_b", "agent_c"])

# Join results
workflow.add_edge(["agent_a", "agent_b", "agent_c"], "aggregator")
workflow.add_edge("aggregator", END)
```

---

## NODE IMPLEMENTATION PATTERNS

### Node 1: Retrieve Context

```python
async def retrieve_context_node(state: AgentState) -> Dict[str, Any]:
    """
    Standard memory retrieval node

    Responsibilities:
    1. Initialize MemoryManager (Mem0)
    2. Retrieve semantic memories
    3. Fetch recent thread messages
    4. Return enriched context
    """
    memory = MemoryManager(
        tenant_id=state["tenant_id"],
        agent_id=state["agent_id"],
        agent_traits=state.get("traits", {})
    )

    context = await memory.get_agent_context(
        user_input=state["input_text"],
        session_id=state["thread_id"],
        k=5
    )

    return {
        "memory_context": context.model_dump(),
        "retrieved_memories": context.retrieved_memories,
        "recent_messages": context.recent_messages,
        "workflow_status": "context_retrieved"
    }
```

### Node 2: Build Prompt

```python
async def build_prompt_node(state: AgentState) -> Dict[str, Any]:
    """
    Construct LLM prompt from agent contract + memory

    Responsibilities:
    1. Load system prompt from agent contract
    2. Inject memory context
    3. Add recent conversation history
    4. Format for LLM consumption
    """
    # Load system prompt
    agent_contract = state["agent_contract"]
    identity = agent_contract.get("identity", {})
    traits = agent_contract.get("traits", {})

    # Build base system prompt
    system_prompt = f"""
You are {agent_contract['name']}.

Identity:
{identity.get('short_description', '')}

Character Role: {identity.get('character_role', '')}
Mission: {identity.get('mission', '')}
Interaction Style: {identity.get('interaction_style', '')}

Personality Traits:
- Creativity: {traits.get('creativity', 50)}/100
- Empathy: {traits.get('empathy', 50)}/100
- Assertiveness: {traits.get('assertiveness', 50)}/100
- Verbosity: {traits.get('verbosity', 50)}/100
"""

    # Inject memory context
    memories = state.get("retrieved_memories", [])
    if memories:
        memory_text = "\n".join([
            f"- {m['content']}" for m in memories[:3]
        ])
        system_prompt += f"\n\nRelevant Memories:\n{memory_text}"

    # Build message list for LLM
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add recent conversation
    for msg in state.get("recent_messages", []):
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current user input
    messages.append({
        "role": "user",
        "content": state["input_text"]
    })

    return {
        "system_prompt": system_prompt,
        "llm_messages": messages,
        "workflow_status": "prompt_built"
    }
```

### Node 3: Invoke LLM

```python
async def invoke_llm_node(state: AgentState) -> Dict[str, Any]:
    """
    Call LLM with constructed prompt

    Responsibilities:
    1. Instantiate LLM from agent configuration
    2. Bind tools if enabled
    3. Invoke LLM
    4. Handle tool calls if present
    5. Return response
    """
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic

    # Get LLM config
    config = state["configuration"]
    llm_provider = config.get("llm_provider", "openai")
    llm_model = config.get("llm_model", "gpt-4o-mini")
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 500)

    # Instantiate LLM
    if llm_provider == "openai":
        llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    elif llm_provider == "anthropic":
        llm = ChatAnthropic(
            model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    # Bind tools if enabled
    if config.get("tools_enabled"):
        from agents.tools import get_agent_tools
        tools = get_agent_tools(state["agent_id"])
        llm = llm.bind_tools(tools)

    # Invoke LLM
    messages = state["llm_messages"]
    response = await llm.ainvoke(messages)

    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        return {
            "tool_calls": response.tool_calls,
            "llm_response": response.content,
            "workflow_status": "tools_requested"
        }

    return {
        "llm_response": response.content,
        "workflow_status": "llm_invoked"
    }
```

### Node 4: Post-Process

```python
async def post_process_node(state: AgentState) -> Dict[str, Any]:
    """
    Post-process LLM response

    Responsibilities:
    1. Clean up response text
    2. Apply formatting rules
    3. Validate response
    4. Apply safety filters
    """
    llm_response = state.get("llm_response", "")

    # Clean up response
    response_text = llm_response.strip()

    # Apply verbosity preference
    verbosity = state["traits"].get("verbosity", 50)
    if verbosity < 30:
        # Make more concise
        response_text = truncate_response(response_text, max_sentences=3)
    elif verbosity > 70:
        # Keep detailed
        pass

    # Apply safety filters
    if state["configuration"].get("safety", 80) > 70:
        response_text = apply_safety_filter(response_text)

    return {
        "response_text": response_text,
        "workflow_status": "post_processed"
    }
```

### Node 5: Check Cognitive Triggers

```python
async def check_triggers_node(state: AgentState) -> Dict[str, Any]:
    """
    Check cognitive triggers and inject interventions

    Responsibilities:
    1. Check reflex triggers (emotion, goal progress)
    2. Inject intervention prompts if threshold exceeded
    3. Modify response if needed
    4. Return final state
    """
    from services.trigger_logic import check_and_handle_triggers

    # Check triggers
    intervention_prompts = await check_and_handle_triggers(
        user_id=state["user_id"],
        agent_id=state["agent_id"],
        tenant_id=state["tenant_id"],
        agent_contract=state["agent_contract"],
        context={
            "user_input": state["input_text"],
            "agent_response": state["response_text"]
        }
    )

    if intervention_prompts:
        # Trigger fired - may modify response
        logger.info(f"Cognitive triggers fired: {len(intervention_prompts)}")

        return {
            "cognitive_triggers": intervention_prompts,
            "trigger_fired": True,
            "workflow_status": "triggers_fired"
        }

    return {
        "cognitive_triggers": [],
        "trigger_fired": False,
        "workflow_status": "completed"
    }
```

---

## ERROR HANDLING & RESILIENCE

### Node-Level Error Handling

```python
async def safe_node(state: AgentState) -> Dict[str, Any]:
    """
    Standard error handling pattern for nodes
    """
    try:
        # Node logic
        result = await perform_operation(state)

        return {
            "result": result,
            "workflow_status": "success"
        }

    except ValueError as e:
        # Validation error - return error state
        logger.error(f"Validation error in node: {e}")
        return {
            "error_message": str(e),
            "workflow_status": "validation_failed"
        }

    except Exception as e:
        # Unexpected error - log and return graceful degradation
        logger.exception(f"Unexpected error in node: {e}")
        return {
            "error_message": "An unexpected error occurred",
            "workflow_status": "failed"
        }
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def invoke_llm_with_retry(llm, messages):
    """Retry LLM calls with exponential backoff"""
    return await llm.ainvoke(messages)
```

### Conditional Error Recovery

```python
def error_recovery_router(state: AgentState) -> str:
    """Route to recovery path on error"""
    if "error_message" in state:
        error_type = state.get("workflow_status")

        if error_type == "memory_retrieval_failed":
            return "use_default_prompt"
        elif error_type == "llm_invoked_failed":
            return "use_fallback_llm"
        else:
            return "log_and_fail"

    return "continue"

workflow.add_conditional_edges(
    "risky_node",
    error_recovery_router,
    {
        "use_default_prompt": "fallback_prompt_node",
        "use_fallback_llm": "fallback_llm_node",
        "log_and_fail": END,
        "continue": "next_node"
    }
)
```

---

## TESTING & VALIDATION

### Unit Testing LangGraph Nodes

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_retrieve_context_node():
    """Test memory retrieval node"""
    # Mock state
    state = {
        "tenant_id": "test-tenant",
        "agent_id": "test-agent",
        "thread_id": "test-thread",
        "input_text": "Hello",
        "traits": {}
    }

    # Mock MemoryManager
    with patch('memoryManager.memory_manager.MemoryManager') as MockMemory:
        mock_memory = MockMemory.return_value
        mock_memory.get_agent_context = AsyncMock(return_value={
            "retrieved_memories": [],
            "recent_messages": [],
            "confidence_score": 0.0
        })

        # Execute node
        result = await retrieve_context_node(state)

        # Assertions
        assert "memory_context" in result
        assert result["workflow_status"] == "context_retrieved"
        mock_memory.get_agent_context.assert_called_once()
```

### Integration Testing Complete Workflow

```python
@pytest.mark.asyncio
async def test_complete_agent_workflow():
    """Test complete agent workflow end-to-end"""
    # Build graph
    graph = build_agent_workflow()

    # Initial state
    initial_state = {
        "agent_id": "test-agent",
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "thread_id": "test-thread",
        "input_text": "Tell me about AI",
        "agent_contract": load_test_contract(),
        "traits": {"verbosity": 50},
        "configuration": {"llm_provider": "openai"}
    }

    # Execute workflow
    result = await graph.ainvoke(initial_state)

    # Assertions
    assert result["workflow_status"] == "completed"
    assert "response_text" in result
    assert len(result["response_text"]) > 0
```

### Testing Multi-Agent Orchestration

```python
@pytest.mark.asyncio
async def test_supervisor_routing():
    """Test supervisor routes to correct subgraph"""
    supervisor = create_supervisor_graph()

    state = {
        "user_request": "Research quantum computing",
        "team_results": {},
        "workflow_status": "pending"
    }

    result = await supervisor.ainvoke(state)

    # Should route to research team
    assert result["current_team"] == "research_team"
    assert "team_results" in result
```

---

## PRODUCTION DEPLOYMENT PATTERNS

### Checkpointer for State Persistence

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Initialize PostgreSQL checkpointer
checkpointer = PostgresSaver(
    connection_string="postgresql://user:pass@localhost:5432/db"
)

# Compile graph with checkpointer
graph = workflow.compile(checkpointer=checkpointer)

# Invoke with thread_id for persistence
result = await graph.ainvoke(
    initial_state,
    config={"configurable": {"thread_id": "user-123-conversation"}}
)
```

### Streaming for Real-Time Responses

```python
async def stream_agent_response(graph, initial_state):
    """Stream agent execution for real-time updates"""
    async for event in graph.astream(initial_state):
        node_name = list(event.keys())[0]
        node_output = event[node_name]

        # Send updates to client
        yield {
            "node": node_name,
            "status": node_output.get("workflow_status"),
            "partial_response": node_output.get("response_text", "")
        }
```

### Human-in-the-Loop Interrupts

```python
from langgraph.checkpoint.memory import MemorySaver

# Compile with interrupt before sensitive node
graph = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["execute_payment"]
)

# First invocation (stops at interrupt)
result = await graph.ainvoke(state, config={"thread_id": "tx-123"})

# Get state at interrupt
current_state = await graph.aget_state(config={"thread_id": "tx-123"})

# User reviews and approves

# Resume execution
result = await graph.ainvoke(
    None,  # No new input, resume from checkpoint
    config={"thread_id": "tx-123"}
)
```

---

## REFERENCE IMPLEMENTATION

### Complete Production-Ready Agent

```python
"""
production_agent.py

Complete production agent with all standards compliance
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import logging

from memoryManager.memory_manager import MemoryManager
from models.agent import AgentContract
from services.trigger_logic import check_and_handle_triggers
from database import get_pg_pool

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Production agent state schema"""
    # Identity
    agent_id: str
    tenant_id: str
    user_id: str
    thread_id: str

    # Input/Output
    input_text: str
    response_text: str

    # Agent configuration
    agent_contract: Dict[str, Any]
    system_prompt: str

    # Memory
    memory_context: Dict[str, Any]
    retrieved_memories: List[Dict[str, Any]]
    recent_messages: List[Dict[str, Any]]

    # LLM
    llm_messages: List[Dict[str, str]]
    llm_response: str

    # Cognitive
    cognitive_triggers: List[str]
    trigger_fired: bool

    # Metadata
    traits: Dict[str, int]
    configuration: Dict[str, Any]
    workflow_status: str


async def retrieve_context(state: AgentState) -> Dict[str, Any]:
    """Node 1: Retrieve memory context"""
    memory = MemoryManager(
        tenant_id=state["tenant_id"],
        agent_id=state["agent_id"],
        agent_traits=state.get("traits", {})
    )

    context = await memory.get_agent_context(
        user_input=state["input_text"],
        session_id=state["thread_id"],
        k=5
    )

    return {
        "memory_context": {"confidence": context.confidence_score},
        "retrieved_memories": context.retrieved_memories,
        "recent_messages": context.recent_messages,
        "workflow_status": "context_retrieved"
    }


async def build_prompt(state: AgentState) -> Dict[str, Any]:
    """Node 2: Build LLM prompt"""
    contract = state["agent_contract"]
    identity = contract.get("identity", {})
    traits = state["traits"]

    system_prompt = f"""
You are {contract['name']}.

{identity.get('short_description', '')}

Traits: Creativity {traits.get('creativity', 50)}/100,
        Empathy {traits.get('empathy', 50)}/100
"""

    memories = state.get("retrieved_memories", [])
    if memories:
        memory_text = "\n".join([m["content"] for m in memories[:3]])
        system_prompt += f"\n\nRelevant context:\n{memory_text}"

    messages = [{"role": "system", "content": system_prompt}]

    for msg in state.get("recent_messages", [])[-5:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": state["input_text"]})

    return {
        "system_prompt": system_prompt,
        "llm_messages": messages,
        "workflow_status": "prompt_built"
    }


async def invoke_llm(state: AgentState) -> Dict[str, Any]:
    """Node 3: Invoke LLM"""
    config = state["configuration"]
    llm = ChatOpenAI(
        model=config.get("llm_model", "gpt-4o-mini"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("max_tokens", 500)
    )

    response = await llm.ainvoke(state["llm_messages"])

    return {
        "llm_response": response.content,
        "workflow_status": "llm_invoked"
    }


async def post_process(state: AgentState) -> Dict[str, Any]:
    """Node 4: Post-process response"""
    response = state["llm_response"].strip()

    # Apply verbosity
    verbosity = state["traits"].get("verbosity", 50)
    if verbosity < 30:
        # Truncate to 3 sentences
        sentences = response.split(". ")
        response = ". ".join(sentences[:3]) + "."

    return {
        "response_text": response,
        "workflow_status": "post_processed"
    }


async def check_triggers(state: AgentState) -> Dict[str, Any]:
    """Node 5: Check cognitive triggers"""
    interventions = await check_and_handle_triggers(
        user_id=state["user_id"],
        agent_id=state["agent_id"],
        tenant_id=state["tenant_id"],
        agent_contract=state["agent_contract"],
        context={"input": state["input_text"]}
    )

    return {
        "cognitive_triggers": interventions,
        "trigger_fired": len(interventions) > 0,
        "workflow_status": "completed"
    }


def build_production_agent() -> StateGraph:
    """Build production agent workflow"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("build_prompt", build_prompt)
    workflow.add_node("invoke_llm", invoke_llm)
    workflow.add_node("post_process", post_process)
    workflow.add_node("check_triggers", check_triggers)

    # Define flow
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "build_prompt")
    workflow.add_edge("build_prompt", "invoke_llm")
    workflow.add_edge("invoke_llm", "post_process")
    workflow.add_edge("post_process", "check_triggers")
    workflow.add_edge("check_triggers", END)

    return workflow.compile()


async def run_agent(
    agent_contract: AgentContract,
    user_id: str,
    tenant_id: str,
    thread_id: str,
    user_input: str
) -> Dict[str, Any]:
    """
    Run production agent with input

    Args:
        agent_contract: Agent JSON contract
        user_id: User UUID
        tenant_id: Tenant UUID
        thread_id: Thread UUID
        user_input: User message

    Returns:
        Agent response with metadata
    """
    graph = build_production_agent()

    initial_state = {
        "agent_id": agent_contract.id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "input_text": user_input,
        "agent_contract": agent_contract.model_dump(),
        "traits": agent_contract.traits.model_dump(),
        "configuration": agent_contract.configuration.model_dump(),
        "workflow_status": "pending"
    }

    result = await graph.ainvoke(initial_state)

    # Store interaction
    memory = MemoryManager(tenant_id, agent_contract.id, agent_contract.traits.model_dump())
    await memory.process_interaction(
        user_input=user_input,
        agent_response=result["response_text"],
        session_id=thread_id,
        user_id=user_id
    )

    return {
        "response": result["response_text"],
        "metadata": {
            "workflow_status": result["workflow_status"],
            "memory_confidence": result["memory_context"]["confidence"],
            "trigger_fired": result["trigger_fired"]
        }
    }
```

---

## SUMMARY: THE ORCHESTRATION COMMANDMENTS

### 10 Immutable Laws

1. **LangGraph is the ONLY orchestrator** - NO custom state machines or loops
2. **State is TypedDict** - Explicit schema, no hidden state
3. **Nodes are pure async functions** - Read state, return updates
4. **Memory is Mem0 + PostgreSQL** - NO local vector stores
5. **Tools are LangChain BaseTool** - Use `@tool` decorator or subclass
6. **Multi-agent is nested StateGraphs** - Hierarchical composition
7. **Errors return state updates** - NO exceptions bubble up
8. **Checkpointers enable persistence** - PostgreSQL or Memory
9. **Streaming for real-time UX** - Use `graph.astream()`
10. **Test every node independently** - Unit + integration tests

### Universal Application Pattern

```
User Request → LangGraph Entry → [Node 1, Node 2, ..., Node N] → Final State
                    ↓                           ↓                       ↓
              StateGraph Compiler          State Updates          Response + Metadata
```

### File Structure (Standard Project Layout)

```
project/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py           # Base agent patterns
│   │   └── guide_agent/
│   │       ├── guide_agent.py      # Main orchestrator
│   │       └── guide_sub_agents/   # Sub-agent nodes
│   ├── graph/
│   │   ├── __init__.py
│   │   └── graph.py                # Workflow definitions
│   ├── memoryManager/
│   │   ├── __init__.py
│   │   └── memory_manager.py       # Mem0 integration
│   ├── tools/
│   │   ├── __init__.py
│   │   └── agent_tools.py          # LangChain tools
│   ├── models/
│   │   ├── __init__.py
│   │   └── agent.py                # Pydantic models (AgentContract)
│   ├── routers/
│   │   └── agents.py               # FastAPI endpoints
│   └── main.py
└── docs/
    └── architecture/
        └── knowledgebase/
            ├── AGENT_CREATION_STANDARD.md
            └── AGENT_ORCHESTRATION_STANDARD.md  # This document
```

---

## END OF AGENT ORCHESTRATION STANDARD

**Generated:** 2025-01-15
**Based On:**
- AGENT_CREATION_STANDARD.md (JSON contract-first design)
- STACK_1ST_PRINCIPLES_GUARDRAIL.md (Technology stack enforcement)
- LangGraph documentation (Core, Multi-Agent, Tools)
- AffirmationApplication production implementation

**This standard is IMMUTABLE. All agent systems MUST comply.**

Use this blueprint alongside AGENT_CREATION_STANDARD.md for complete agent development.

**LangGraph + LangChain + Mem0 + PostgreSQL = Universal Agent Architecture**
