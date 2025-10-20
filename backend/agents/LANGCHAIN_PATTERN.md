# LangChain Pattern Adaptation for Multi-Agent System

## Overview

This document describes the **contract-driven prompt template pattern** adapted from `supervisor_READONLY_AGENTEXMPL.py` and applied to our multi-agent content creation system.

## Pattern Source

**Original Example:** `ExampleRepoREADONLY/supervisor_READONLY_AGENTEXMPL.py` (JewelryBox AI)

**Key Innovation:** Using agent JSON contracts as the single source of truth for prompts, combined with LangChain's `ChatPromptTemplate` for history-aware conversations.

---

## Architecture Components

### 1. Agent JSON Contract (Source of Truth)

**Location:** `backend/agents/prompts/{agent_id}.json`

Each agent has a JSON contract that defines:
- **Agent identity** (id, name, role, description)
- **Responsibilities** (what the agent does)
- **Capabilities** (what the agent can do)
- **Inputs/Outputs** (data schema)
- **Prompt Template** (system prompt with variables)
- **LangChain Integration** (pattern documentation)

**Example:**
```json
{
  "agent_id": "supervisor_agent",
  "prompt_template": {
    "system": "You are the SupervisorAgent...\n\n## MEMORY CONTEXT\n{memory_context}\n\n## CAMPAIGN HISTORY\n{campaign_history}\n\n## CURRENT COST USAGE\n- Daily: ${daily_cost_usd:.2f} / ${max_daily_cost_usd:.2f}\n...",
    "variables": ["memory_context", "campaign_history", "daily_cost_usd", "max_daily_cost_usd", "cost_limit_usd"]
  },
  "langchain_integration": {
    "pattern": "ChatPromptTemplate with history support",
    "components": {
      "prompt_template": "ChatPromptTemplate.from_messages([SystemMessagePromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate])",
      "chain": "prompt_template | llm_with_structured_output",
      "response_processor": "process_supervisor_response(user_input, decision, memory_context)"
    }
  }
}
```

### 2. Chain Creation Function

**Location:** `backend/agents/supervisor_agent.py:94-155`

```python
def create_supervisor_chain(
    agent_config: Dict[str, Any],
    memory_context: Dict[str, Any],
    cost_info: Dict[str, float]
) -> tuple[ChatPromptTemplate, Any]:
    """
    Create LangChain prompt template and chain from agent JSON contract.

    Steps:
    1. Load system prompt from agent contract
    2. Format with current context (memory, cost, etc.)
    3. Build ChatPromptTemplate with history support
    4. Create chain: prompt_template | llm

    Returns:
        Tuple of (prompt_template, chain)
    """
    # Get base system prompt from agent contract
    system_prompt_template = agent_config.get("prompt_template", {}).get("system", "")

    # Format with current context
    system_prompt = system_prompt_template.format(
        memory_context=_format_memory_context(memory_context),
        campaign_history=_format_campaign_history(memory_context.get("campaign_history", [])),
        daily_cost_usd=cost_info.get("daily_cost_usd", 0.0),
        max_daily_cost_usd=cost_info.get("max_daily_cost_usd", 50.0),
        cost_limit_usd=cost_info.get("cost_limit_usd", 5.0)
    )

    # Build ChatPromptTemplate with history support
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{user_input}")
    ])

    # Create LLM with structured output
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.3)
    llm_with_structure = llm.with_structured_output(SupervisorDecision)

    # Create chain
    chain = prompt_template | llm_with_structure

    return prompt_template, chain
```

### 3. Unified Response Processor

**Location:** `backend/agents/supervisor_agent.py:158-231`

```python
def process_supervisor_response(
    user_input: str,
    decision: SupervisorDecision,
    memory_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Unified response processor for supervisor decisions.

    Equivalent to process_ai_response(user_input, ai_response) from example.

    Steps:
    1. Generate conversational chat response from structured decision
    2. Inject memory references (similar to inject_relevant_url)
    3. Return processed response dict

    Returns:
        {
            "chat_response": "...",
            "decision": {...},
            "memory_injected": true,
            "timestamp": "..."
        }
    """
    # Generate conversational response
    chat_response = _generate_chat_response_from_decision(
        decision=decision,
        user_input=user_input,
        memory_context=memory_context
    )

    # Inject memory references
    chat_response = _inject_memory_references(chat_response, memory_context)

    return {
        "chat_response": chat_response,
        "decision": decision.model_dump(),
        "memory_injected": True,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 4. Node Implementation (LangGraph)

**Location:** `backend/agents/supervisor_agent.py:234-413`

```python
@safe_node_execution("supervisor")
async def supervisor_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    SupervisorAgent node with LangChain pattern.

    Workflow:
    1. Load agent config from JSON contract (registry)
    2. Retrieve memory context (Mem0 + Qdrant)
    3. Create ChatPromptTemplate and chain
    4. Invoke chain with user_input and conversation history
    5. Process response with unified response processor
    6. Route to next agent or END
    """
    # STEP 1: Load agent config
    registry = get_agent_registry()
    agent_config = registry.get_agent("supervisor_agent")

    # STEP 2: Retrieve memory context
    memory_context = await _retrieve_supervisor_context(...)

    # STEP 3: Get cost tracking info
    cost_info = {...}

    # STEP 4: Create chain
    prompt_template, chain = create_supervisor_chain(
        agent_config=agent_config,
        memory_context=memory_context,
        cost_info=cost_info
    )

    # STEP 5: Prepare conversation history
    history = [
        HumanMessage(content=msg["content"]) if msg["role"] == "user"
        else SystemMessage(content=msg["content"])
        for msg in state.get("messages", [])[-10:]
    ]

    # STEP 6: Invoke chain
    decision = await chain.ainvoke({
        "user_input": user_request,
        "history": history
    })

    # STEP 7: Process response
    processed = process_supervisor_response(
        user_input=user_request,
        decision=decision,
        memory_context=memory_context
    )

    # STEP 8: Route based on decision.action
    if decision.action == "create_content":
        return {...}  # Route to content_creation
    elif decision.action == "clarify":
        return {...}  # Return clarification prompt
    else:  # reject
        return {...}  # Return error message
```

---

## Key Patterns from Example

### Pattern 1: System Prompt Construction

**From Example:**
```python
system_data = AGENT_ROLES["jewelry_ai"][0]["systemPrompt"]
system_prompt = f"""You are {system_data['identity']}, serving as {system_data['role']}.
Tone: {system_data['tone']}
...
{chr(10).join(system_data['description'])}
..."""
```

**Our Adaptation:**
```python
# Load from JSON contract
system_prompt_template = agent_config.get("prompt_template", {}).get("system", "")

# Format with current context
system_prompt = system_prompt_template.format(
    memory_context=memory_str,
    campaign_history=campaign_history_str,
    daily_cost_usd=cost_info.get("daily_cost_usd", 0.0),
    ...
)
```

**Key Difference:**
- **Example:** Hardcoded JSON structure with nested dicts
- **Our System:** Templated string with Python .format() for flexibility

### Pattern 2: ChatPromptTemplate with History

**From Example:**
```python
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{user_input}")
])
chain = prompt_template | llm
```

**Our Adaptation:**
```python
# Identical pattern!
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{user_input}")
])

# Enhanced with structured output
llm_with_structure = llm.with_structured_output(SupervisorDecision)
chain = prompt_template | llm_with_structure
```

**Key Enhancement:**
- We add `.with_structured_output(SupervisorDecision)` for type-safe responses

### Pattern 3: Unified Response Processor

**From Example:**
```python
def process_ai_response(user_input: str, ai_response: str) -> str:
    try:
        processed_response = inject_relevant_url(user_input, ai_response)
        return processed_response
    except Exception as e:
        logger.error(f"Error processing AI response: {e}")
        return ai_response
```

**Our Adaptation:**
```python
def process_supervisor_response(
    user_input: str,
    decision: SupervisorDecision,
    memory_context: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        # Generate conversational chat response
        chat_response = _generate_chat_response_from_decision(...)

        # Inject memory references (equivalent to inject_relevant_url)
        chat_response = _inject_memory_references(chat_response, memory_context)

        return {
            "chat_response": chat_response,
            "decision": decision.model_dump(),
            "memory_injected": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing supervisor response: {e}")
        return {...}  # Fallback response
```

**Key Enhancement:**
- Instead of injecting URLs, we inject **memory references** (past campaigns, user preferences)
- Returns structured dict instead of just string

---

## Benefits of This Pattern

### 1. **Single Source of Truth**
- All agent behavior defined in JSON contracts
- Easy to update prompts without touching code
- Version control for agent identity/behavior

### 2. **Memory-Aware Conversations**
- `MessagesPlaceholder` maintains conversation history
- Agents remember past interactions within session
- Consistent multi-turn dialogue

### 3. **Structured Output (Type Safety)**
- Pydantic models ensure response schema compliance
- No JSON parsing errors from LLM hallucinations
- Clear contract between agents

### 4. **Testability**
- Mock agent configs easily
- Test chain creation independently
- Validate response processing logic

### 5. **Extensibility**
- Add new agents by creating JSON contracts
- Reuse chain creation pattern across agents
- Unified response processing for all agents

---

## Comparison: Example vs Our System

| Aspect | Example (JewelryBox AI) | Our System (Content Creation) |
|--------|-------------------------|-------------------------------|
| **Agent Definition** | Hardcoded JSON in Python | JSON contracts in `prompts/` |
| **Prompt Source** | Nested dict access | Registry with validation |
| **History Support** | `MessagesPlaceholder` | `MessagesPlaceholder` (same) |
| **Response Type** | String | Pydantic model + processed dict |
| **Memory Injection** | `inject_relevant_url` | `_inject_memory_references` |
| **State Management** | In-memory only | LangGraph state + DB persistence |
| **Multi-Agent** | Single agent | Multi-agent orchestration |
| **Cost Tracking** | Not mentioned | Integrated with limits |

---

## Usage Example

### Creating a New Agent with This Pattern

1. **Define JSON Contract:**

```json
{
  "agent_id": "my_new_agent",
  "prompt_template": {
    "system": "You are MyNewAgent...\n\n{context_variable}",
    "variables": ["context_variable"]
  },
  "outputs": {
    "decision_schema": {
      "type": "MyAgentDecision",
      "fields": {...}
    }
  }
}
```

2. **Create Chain Function:**

```python
def create_my_agent_chain(agent_config, context):
    system_prompt = agent_config["prompt_template"]["system"].format(
        context_variable=context["data"]
    )

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{user_input}")
    ])

    llm_with_structure = llm.with_structured_output(MyAgentDecision)
    chain = prompt_template | llm_with_structure

    return prompt_template, chain
```

3. **Implement Node:**

```python
@safe_node_execution("my_new_agent")
async def my_agent_node(state: WorkflowState) -> Dict[str, Any]:
    # Load config
    agent_config = registry.get_agent("my_new_agent")

    # Create chain
    prompt_template, chain = create_my_agent_chain(agent_config, context)

    # Invoke
    decision = await chain.ainvoke({"user_input": input, "history": history})

    # Process
    processed = process_my_agent_response(input, decision)

    return {...}  # State updates
```

---

## Next Steps

### Extend to Other Agents

1. **ContentCreationAgent** → Script generation with memory awareness
2. **TikTokAgent** → Platform publishing with past performance insights
3. **YouTubeShortsAgent** → SEO optimization based on successful videos

### Enhance Response Processing

- Add more sophisticated memory injection logic
- Implement A/B testing for prompt variations
- Track response quality metrics

### Add Agent Registry Features

- Hot-reload agent configs without restart
- Validate contracts against schema
- Version management for agent evolution

---

## References

- **Example File:** `ExampleRepoREADONLY/supervisor_READONLY_AGENTEXMPL.py`
- **LangChain Docs:** [ChatPromptTemplate](https://python.langchain.com/docs/modules/model_io/prompts/prompt_templates/)
- **Our Implementation:** `backend/agents/supervisor_agent.py`
- **Agent Registry:** `backend/agents/registry.py`
- **JSON Contracts:** `backend/agents/prompts/`
