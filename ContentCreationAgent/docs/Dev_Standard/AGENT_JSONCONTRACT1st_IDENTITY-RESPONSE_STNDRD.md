# Agent JSON Contract & Identity-First Response Standard

**Version:** 2.0
**Last Updated:** 2025-10-19
**Purpose:** Comprehensive specification for building production-grade AI agents with JSON-driven identity, trait-based behavior, and unified memory integration.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Philosophy](#core-philosophy)
3. [JSON Contract Architecture](#json-contract-architecture)
4. [Agent Identity System](#agent-identity-system)
5. [State Management Pattern](#state-management-pattern)
6. [Response Generation Pipeline](#response-generation-pipeline)
7. [Memory Integration](#memory-integration)
8. [Implementation Guide](#implementation-guide)
9. [Troubleshooting](#troubleshooting)
10. [Reference Implementation](#reference-implementation)

---

## Overview

This standard defines a **JSON-first, identity-driven architecture** for building AI agents that maintain consistent personality, leverage comprehensive memory systems, and generate contextually-aware responses. The system is built on three foundational principles:

1. **JSON Contract First**: Agent configuration drives all behavior through structured JSON files
2. **Identity as Lens**: Agent personality filters memory, context, and response generation
3. **Unified Memory**: Single interface for short-term, long-term, and reinforcement learning

### Key Benefits

- **Reproducibility**: Any agent can be recreated from JSON configuration
- **Consistency**: Personality traits mathematically influence all agent behavior
- **Scalability**: Clear separation between configuration, state, and runtime
- **Debuggability**: Every decision traced back to identity contract
- **Portability**: Standard works across any LangChain/LangGraph application

---

## Core Philosophy

### Identity-First Design

Every agent starts with a **JSON identity contract** that defines:

```
WHO the agent is → WHAT they believe → HOW they communicate → WHY they exist
```

This identity becomes the **filtering lens** through which all information flows:

- **Memory Retrieval**: Memories aligned with identity receive higher relevance scores
- **Response Generation**: Traits mathematically adjust temperature, token limits, formality
- **Context Building**: Agent identity determines which context is important
- **Reinforcement Learning**: Feedback adjusts traits within identity boundaries

### The JSON Contract Pattern

```
Form Input → JSON Files → Database → Runtime State → Agent Response
     ↓            ↓            ↓           ↓              ↓
  Human      Structure    Storage    Execution      Personality
   Data      Definition   Persistence  Context        Output
```

### Three-Layer Architecture

1. **Configuration Layer** (Static JSON)
   - `agent_specific_prompt.json`: System prompt template with trait placeholders
   - `agent_attributes.json`: Complete agent configuration and metadata

2. **State Layer** (Runtime TypedDict)
   - `AgentState`: Conversation state, memory context, workflow control
   - `GraphState`: LangGraph-native state schema for graph execution

3. **Memory Layer** (Unified Interface)
   - Short-term: Thread history (last N messages)
   - Long-term: Semantic vector storage (Mem0/Qdrant)
   - Reinforcement: Trait adjustments from user feedback

---

## JSON Contract Architecture

### File 1: `agent_specific_prompt.json`

**Purpose**: Template-driven system prompt with personality trait integration

**Location**: `backend/prompts/{agent_id}/agent_specific_prompt.json`

**Structure**:

```json
{
  "system_prompt": "You are {name}, {shortDescription}.\n\n**Your Identity:**\n{identity}\n\n**Your Mission:**\n{mission}\n\n**Interaction Style:**\n{interactionStyle}\n\n**Personality Traits (0-100 scale):**\n- Creativity: {creativity}/100\n- Empathy: {empathy}/100\n- Assertiveness: {assertiveness}/100\n- Verbosity: {verbosity}/100\n- Formality: {formality}/100\n- Confidence: {confidence}/100\n- Humor: {humor}/100\n- Technicality: {technicality}/100\n- Safety: {safety}/100\n\nRespond as this character consistently throughout the conversation.",

  "variables": {
    "name": "string",
    "shortDescription": "string",
    "identity": "string",
    "mission": "string",
    "interactionStyle": "string",
    "creativity": "number",
    "empathy": "number",
    "assertiveness": "number",
    "verbosity": "number",
    "formality": "number",
    "confidence": "number",
    "humor": "number",
    "technicality": "number",
    "safety": "number"
  },

  "metadata": {
    "agent_id": "uuid",
    "version": "1.0",
    "created": "ISO8601 timestamp",
    "supports_voice": true,
    "supports_memory": true
  }
}
```

**Key Principles**:

- **Placeholder Variables**: Use `{variable_name}` for dynamic substitution
- **Trait Integration**: All 9 core traits must be referenced in the prompt
- **Character Consistency**: Prompt should reinforce identity in multiple ways
- **Metadata Tracking**: Version and capabilities for backward compatibility

### File 2: `agent_attributes.json`

**Purpose**: Complete agent configuration including performance settings

**Location**: `backend/prompts/{agent_id}/agent_attributes.json`

**Structure**:

```json
{
  "agent_id": "uuid",
  "name": "Agent Name",
  "shortDescription": "Brief description of agent purpose",

  "voice": {
    "elevenlabsVoiceId": "voice_id_string"
  },

  "knowledge": {
    "urls": ["https://example.com/knowledge"],
    "files": ["file_id_1", "file_id_2"]
  },

  "characterDescription": {
    "physicalAppearance": "Description of physical characteristics",
    "identity": "Deep identity statement (who they are, background, motivations)",
    "interactionStyle": "How they communicate and engage with users"
  },

  "avatar": "path/to/avatar/image.png",

  "traits": {
    "creativity": 50,
    "empathy": 50,
    "assertiveness": 50,
    "verbosity": 50,
    "formality": 50,
    "confidence": 50,
    "humor": 30,
    "technicality": 50,
    "safety": 70
  },

  "performance_settings": {
    "max_tokens": 253.6,
    "max_iterations": 1,
    "temperature": 0.94,
    "safety_level": 0.01
  },

  "created_at": "ISO8601 timestamp",
  "version": "1.0"
}
```

**RVR Mapping (Relative Verbosity Response)**:

Performance settings are **derived from traits** using mathematical formulas:

```python
# Max Tokens: Base 80 + Verbosity-scaled range
max_tokens = 80 + (verbosity / 100.0) * 560
# Range: 80 (verbosity=0) to 640 (verbosity=100)

# Temperature: Creativity trait normalized
temperature = creativity / 100.0
# Range: 0.0 to 1.0

# Max Iterations: Verbosity drives response depth
max_iterations = max(1, int(1 + (verbosity / 100.0) * 2))
# Range: 1 to 3

# Safety Level: Safety trait normalized
safety_level = safety / 100.0
# Range: 0.0 to 1.0
```

---

## Agent Identity System

### The Nine Core Traits

Each trait is a **0-100 integer** representing behavioral parameters:

| Trait | Low (0-30) | Medium (31-70) | High (71-100) |
|-------|------------|----------------|---------------|
| **Creativity** | Practical, literal | Balanced approach | Highly creative, abstract |
| **Empathy** | Task-focused | Moderately caring | Deeply empathetic |
| **Assertiveness** | Gentle, accommodating | Moderately assertive | Confident, direct |
| **Verbosity** | Concise, brief | Balanced responses | Detailed explanations |
| **Formality** | Casual, friendly | Semi-formal | Professional, formal |
| **Confidence** | Humble, uncertain | Moderately confident | Very confident |
| **Humor** | Serious | Occasional humor | Witty, playful |
| **Technicality** | Simple explanations | Moderately technical | Highly technical |
| **Safety** | Risk-tolerant | Balanced | Very cautious |

### Identity Components

**Name**: Primary identifier (e.g., "Rick Sanchez")

**Short Description**: One-sentence agent purpose (e.g., "Genius scientist and interdimensional traveler")

**Identity**: 2-4 paragraph deep backstory explaining:
- Who they are fundamentally
- Their background and experiences
- What motivates them
- How they see the world
- Relationships and loyalties

**Mission**: Clear statement of agent purpose (e.g., "Serve as Pete's wingman and provide scientific solutions")

**Interaction Style**: 1-2 paragraphs describing:
- Communication patterns
- Speech mannerisms
- Attitude and tone
- How they handle questions
- Deflection tactics (e.g., for "are you AI?" questions)

### Identity as Memory Filter

The `AgentIdentity` dataclass filters all memory retrieval:

```python
@dataclass
class AgentIdentity:
    name: str
    identity: str
    mission: str
    interaction_style: str
    personality_traits: Dict[str, float]  # 0-100 values
    behavioral_parameters: Dict[str, Any]

    @classmethod
    def from_traits(cls, traits: Dict[str, Any]) -> 'AgentIdentity':
        """Create from agent traits dictionary"""
        return cls(
            name=traits.get('name'),
            identity=traits.get('identity'),
            mission=traits.get('mission'),
            interaction_style=traits.get('interactionStyle'),
            personality_traits={
                'creativity': traits.get('creativity', 50),
                # ... all 9 traits
            },
            behavioral_parameters={
                'response_length': traits.get('verbosity', 50),
                'technical_depth': traits.get('technicality', 50),
                'emotional_tone': traits.get('empathy', 50)
            }
        )
```

---

## State Management Pattern

### GraphState (LangGraph Native)

**Purpose**: Primary state schema for graph execution

```python
class GraphState(TypedDict, total=False):
    session_id: str              # Unique session identifier
    user_id: str                 # Tenant/user for isolation
    agent: AgentPayload          # Full agent configuration
    input_text: str              # Current user input
    thread_context: List[dict]   # Recent conversation history
    mem0_context: List[dict]     # Retrieved long-term memories
    plan: Optional[str]          # Multi-step planning
    tool_actions: List[dict]     # Tool execution results
    response_text: str           # Generated agent response
    events: List[dict]           # Workflow event log
```

**Usage**: All graph nodes receive and return GraphState

### AgentState (Legacy Compatibility)

**Purpose**: Extended state for complex workflows with voice/feedback

```python
class AgentState(TypedDict):
    # Core conversation
    messages: List[dict]
    current_message: str
    agent_id: str
    session_id: str

    # API compatibility
    user_input: str
    input_text: str
    user_id: str
    tenant_id: str
    traits: Dict[str, Any]
    model: str

    # Agent configuration
    agent_config: Dict[str, Any]
    max_tokens: int
    max_iterations: int
    tool_routing_threshold: float

    # Memory context
    short_term_context: str
    persistent_context: str
    conversation_history: List[Dict[str, Any]]
    thread_context: List[dict]
    mem0_context: List[dict]

    # Voice and audio
    voice_id: str
    audio_data: Optional[bytes]
    transcription: str
    tts_enabled: bool

    # Workflow control
    iteration_count: int
    workflow_status: str  # "active", "completed", "error"
    error_message: Optional[str]
    agent_response: Optional[str]
    response_text: str

    # Feedback and learning
    user_feedback: Optional[Dict[str, Any]]
    reflection_data: Dict[str, Any]

    # Performance metrics
    start_time: float
    processing_time: float
    tokens_used: int
```

### State Helper Functions

```python
def update_state(state: AgentState, **updates) -> AgentState:
    """Update state immutably with new values"""
    new_state = state.copy()
    for key, value in updates.items():
        new_state[key] = value
    return new_state

def create_initial_state(agent_config: Dict, session_id: str) -> AgentState:
    """Create initial state from agent configuration"""
    return AgentState(
        agent_id=agent_config.get("id"),
        session_id=session_id,
        messages=[],
        workflow_status="active",
        # ... initialize all fields
    )
```

---

## Response Generation Pipeline

### High-Level Flow

```
User Input → Memory Retrieval → Prompt Building → LLM Generation → Memory Storage → Response
```

### Step 1: Input Validation

**File**: `backend/agents/nodes/agent_node.py:18-42`

```python
async def generate_agent_response(state: Dict[str, Any]) -> str:
    # Extract required inputs from state
    session_id = state.get("session_id")
    tenant_id = state.get("tenant_id") or state.get("user_id", "default")
    user_input = state.get("user_input") or state.get("input_text") or state.get("current_message")
    traits = state.get("traits", {})
    agent_config = state.get("agent_config", {})

    # Validate required fields
    if not session_id:
        raise ValueError("session_id is required")
    if not user_input:
        raise ValueError("user_input is required")
    if not traits and not agent_config:
        raise ValueError("traits dictionary or agent_config is required")
```

**Key Principle**: Handle multiple state schemas (GraphState vs AgentState) gracefully

### Step 2: Memory Context Retrieval

**File**: `backend/agents/nodes/agent_node.py:58-66`

```python
# Initialize unified memory manager with agent identity
agent_id = state.get("agent_id") or session_id
memory_manager = create_memory_manager(tenant_id, agent_id, traits)

# Get comprehensive memory context
memory_context = await memory_manager.get_agent_context(user_input, session_id)

# Memory context contains:
# - thread_history: Recent conversation messages
# - relevant_memories: Top-K semantic matches from long-term storage
# - reinforcement_adjustments: Trait deltas from user feedback
# - reflection_insights: Agent self-reflection summaries
# - confidence_score: Memory availability confidence (0-1)
# - context_summary: Human-readable context description
```

### Step 3: Prompt Building with Identity

**File**: `backend/agents/prompt_loader.py:8-51`

```python
def load_agent_prompt(payload: AgentPayload) -> str:
    """Load and format agent-specific system prompt from JSON template"""

    # Load JSON template
    schema = json.loads(PROMPT_PATH.read_text(encoding="utf-8"))

    # Extract traits
    traits_json = payload.traits.model_dump()
    character_desc = payload.characterDescription

    # Format with identity variables
    prompt = schema["system_prompt"].format(
        name=payload.name,
        shortDescription=payload.shortDescription,
        identity=character_desc.identity or "",
        mission=payload.mission or "",
        interactionStyle=character_desc.interactionStyle or "",
        # Individual trait values
        creativity=traits_json.get("creativity", 50),
        empathy=traits_json.get("empathy", 50),
        # ... all traits
    )

    return prompt
```

### Step 4: Message Sequence Building

**File**: `backend/agents/nodes/agent_node.py:105-123`

```python
# Build enhanced message sequence with memory context
messages = [SystemMessage(content=system_prompt)]

# Add relevant long-term memories as context
if relevant_memories:
    memory_context_msg = "Relevant context from memory:\n"
    for i, memory in enumerate(relevant_memories[:3]):  # Top 3
        memory_context_msg += f"- {memory.get('text', '')[:200]}...\n"
    messages.append(SystemMessage(content=memory_context_msg))

# Add thread history (short-term memory)
for msg in thread_history:
    if msg['role'] == 'user':
        messages.append(HumanMessage(content=msg['content']))
    elif msg['role'] == 'assistant':
        messages.append(AIMessage(content=msg['content']))

# Add current user input
messages.append(HumanMessage(content=user_input))
```

### Step 5: LLM Configuration from Traits

**File**: `backend/agents/nodes/agent_node.py:125-142`

```python
# Initialize LLM with trait-based configuration
temperature = adjusted_traits.get("creativity", 50) / 100.0
max_tokens = _calculate_max_tokens(adjusted_traits.get("verbosity", 50))

# Apply reinforcement learning adjustments
confidence_adjustment = memory_context.reinforcement_adjustments.get('confidence_delta', 0.0)
temperature = max(0.0, min(1.0, temperature + confidence_adjustment))

llm = ChatOpenAI(
    model=state.get("model", "gpt-4o-mini"),
    temperature=temperature,
    max_tokens=max_tokens,
    openai_api_key=settings.OPENAI_API_KEY
)

# Generate response
response = await llm.ainvoke(messages)
```

**RVR Calculation**:

```python
def _calculate_max_tokens(verbosity: int) -> int:
    """Calculate max tokens based on verbosity trait (0-100)"""
    base_tokens = 50
    max_tokens_cap = 500
    return int(base_tokens + (verbosity / 100.0) * (max_tokens_cap - base_tokens))
```

### Step 6: Memory Processing

**File**: `backend/agents/nodes/agent_node.py:159-168`

```python
# Process complete interaction through unified memory system
interaction_result = await memory_manager.process_interaction(
    user_input=user_input,
    agent_response=response.content,
    session_id=session_id,
    feedback=None  # Added separately via feedback API
)

# This handles:
# - Storing in thread memory (short-term)
# - Adding to persistent memory (Mem0/Qdrant)
# - Triggering reflections if interval reached
# - Updating interaction count
```

---

## Memory Integration

### Unified Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Unified Memory Manager                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Thread     │  │    Mem0      │  │     RL       │      │
│  │   Memory     │  │  Persistent  │  │ Adjustments  │      │
│  │ (Short-term) │  │ (Long-term)  │  │  (Feedback)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        Identity-Filtered Retrieval                    │   │
│  │  Composite Score = α₁·semantic + α₂·recency +         │   │
│  │                    α₃·importance + α₄·reinforcement   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Memory Context Dataclass

```python
@dataclass
class MemoryContext:
    """Unified memory context for agent responses"""
    thread_history: List[Dict[str, Any]]          # Recent messages (last 20)
    relevant_memories: List[Dict[str, Any]]       # Top-K semantic matches
    identity_filter: AgentIdentity                # Agent personality lens
    reinforcement_adjustments: Dict[str, float]   # RL trait deltas
    reflection_insights: List[str]                # Self-reflection summaries
    confidence_score: float                       # Memory quality (0-1)
    context_summary: str                          # Human-readable summary
```

### Memory Retrieval with Composite Scoring

**File**: `backend/memory/unified_memory_manager.py:364-434`

```python
async def _retrieve_relevant_memories(self, query: str) -> List[Dict[str, Any]]:
    """Retrieve relevant memories using composite scoring"""

    # 1. Semantic search via Mem0
    results = self.mem0.search(
        query=query,
        user_id=self.namespace,
        k=self.settings.k
    )

    # 2. Apply composite scoring
    for memory in results:
        # Semantic score (from vector similarity)
        semantic_score = float(memory.get('score', 0.0))

        # Recency score (time decay)
        hours_ago = (now - created_time).total_seconds() / 3600.0
        decay_lambda = 0.693147 / self.settings.decay_halflife_hours
        recency_score = math.exp(-decay_lambda * hours_ago)

        # Importance score (GenerativeAgent pattern)
        importance_score = self._calculate_importance_score(memory)

        # Reinforcement score (feedback history)
        reinforcement_score = memory.get('reinforcement_score', 0.0)

        # Composite score
        composite_score = (
            0.45 * semantic_score +      # α₁ = 45%
            0.35 * recency_score +       # α₂ = 35%
            0.15 * importance_score +    # α₃ = 15%
            0.05 * reinforcement_score   # α₄ = 5%
        )

        memory['composite_score'] = composite_score

    # 3. Sort by composite score
    results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
    return results[:self.settings.k]
```

### Importance Calculation (GenerativeAgent Pattern)

**File**: `backend/memory/unified_memory_manager.py:436-497`

```python
def _calculate_importance_score(self, memory: Dict[str, Any]) -> float:
    """Calculate importance based on GenerativeAgent pattern"""

    text = memory.get('text', '').lower()
    importance_score = 0.0

    # Emotional content (high importance)
    emotional_keywords = ['feel', 'emotion', 'happy', 'sad', 'angry', ...]
    emotional_matches = sum(1 for kw in emotional_keywords if kw in text)
    importance_score += emotional_matches * 0.15

    # Mission/goal relevance
    if self.agent_identity and self.agent_identity.mission:
        mission_keywords = self.agent_identity.mission.lower().split()
        mission_matches = sum(1 for kw in mission_keywords if kw in text and len(kw) > 3)
        importance_score += mission_matches * 0.2

    # Social significance
    social_keywords = ['relationship', 'friend', 'conflict', 'trust', ...]
    social_matches = sum(1 for kw in social_keywords if kw in text)
    importance_score += social_matches * 0.1

    # Novel/detailed information
    if len(text) > 100:
        importance_score += 0.1
    if len(text) > 300:
        importance_score += 0.15

    # Decision-making indicators
    decision_keywords = ['decide', 'plan', 'strategy', 'goal', ...]
    decision_matches = sum(1 for kw in decision_keywords if kw in text)
    importance_score += decision_matches * 0.12

    # Success/failure (high emotional impact)
    outcome_keywords = ['success', 'fail', 'win', 'achieve', ...]
    outcome_matches = sum(1 for kw in outcome_keywords if kw in text)
    importance_score += outcome_matches * 0.18

    return min(importance_score, 1.0)
```

### Identity-Based Memory Filtering

**File**: `backend/memory/unified_memory_manager.py:499-525`

```python
def _apply_identity_filter(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter memories through agent identity lens"""

    if not self.agent_identity or not memories:
        return memories

    # Extract identity keywords
    identity_keywords = [
        self.agent_identity.name.lower(),
        *self.agent_identity.identity.lower().split(),
        *self.agent_identity.mission.lower().split(),
        *self.agent_identity.interaction_style.lower().split()
    ]

    for memory in memories:
        content = memory.get('text', '').lower()

        # Boost score if memory aligns with identity
        identity_relevance = sum(1 for kw in identity_keywords if kw in content)
        if identity_relevance > 0:
            memory['identity_boost'] = identity_relevance * 0.1
            memory['composite_score'] += memory['identity_boost']

    # Re-sort after identity filtering
    memories.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
    return memories
```

### Reinforcement Learning from Feedback

**File**: `backend/memory/unified_memory_manager.py:550-596`

```python
async def _apply_reinforcement_learning(
    self,
    user_input: str,
    agent_response: str,
    feedback: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Apply RL based on user feedback"""

    reward = feedback.get('reward', 0.0)  # -1.0 to 1.0
    feedback_type = feedback.get('type', 'general')

    # Update RL adjustments based on feedback
    if reward > 0.5:  # Positive feedback
        if 'verbose' in feedback_type.lower():
            self.rl_adjustments['verbosity_delta'] += self.settings.learning_rate
        elif 'confident' in feedback_type.lower():
            self.rl_adjustments['confidence_delta'] += self.settings.learning_rate
        elif 'formal' in feedback_type.lower():
            self.rl_adjustments['formality_delta'] += self.settings.learning_rate

    elif reward < -0.5:  # Negative feedback
        # Decrease corresponding traits
        if 'verbose' in feedback_type.lower():
            self.rl_adjustments['verbosity_delta'] -= self.settings.learning_rate
        # ... similar for other traits

    # Clamp adjustments to reasonable bounds [-0.3, 0.3]
    for key in self.rl_adjustments:
        self.rl_adjustments[key] = max(-0.3, min(0.3, self.rl_adjustments[key]))

    # Store reinforcement in persistent memory
    if self.mem0:
        self.mem0.add(
            messages=[{"role": "system", "content": f"Feedback: {feedback_type} with reward {reward}"}],
            user_id=self.namespace,
            metadata={"type": "reinforcement", "reward": reward}
        )

    return {
        "reward": reward,
        "adjustments": self.rl_adjustments.copy(),
        "feedback_type": feedback_type
    }
```

### Reflection Triggering

**File**: `backend/memory/unified_memory_manager.py:598-651`

```python
def _should_reflect(self) -> bool:
    """Determine if reflection should be triggered"""
    now = datetime.now(timezone.utc)
    time_since_reflection = now - self.last_reflection

    return (
        time_since_reflection.total_seconds() > self.settings.reflection_interval_hours * 3600 or
        self.interaction_count % 10 == 0  # Every 10 interactions
    )

async def _generate_reflection(self, session_id: str) -> Optional[str]:
    """Generate reflection on recent interactions"""

    thread_history = self._get_thread_history(session_id)
    recent_messages = thread_history[-self.settings.reflection_window:]

    if not recent_messages:
        return None

    # Create reflection summary
    user_messages = [msg['content'] for msg in recent_messages if msg['role'] == 'user']
    agent_messages = [msg['content'] for msg in recent_messages if msg['role'] == 'assistant']

    reflection_content = (
        f"Reflection on recent interaction: "
        f"User expressed {len(user_messages)} inputs, "
        f"agent provided {len(agent_messages)} responses. "
        f"Current RL adjustments: {self.rl_adjustments}"
    )

    # Store reflection in cache
    global _reflection_cache
    if self.namespace not in _reflection_cache:
        _reflection_cache[self.namespace] = []

    _reflection_cache[self.namespace].append(reflection_content)
    _reflection_cache[self.namespace] = _reflection_cache[self.namespace][-10:]

    self.last_reflection = datetime.now(timezone.utc)
    return reflection_content
```

---

## Implementation Guide

### Step-by-Step: Creating a New Agent

#### 1. Define Agent Identity

Create a JSON payload with complete identity:

```python
agent_request = {
    "name": "Dr. Sarah Chen",
    "shortDescription": "AI Ethics researcher and philosophical guide",

    "identity": """I'm Dr. Sarah Chen, a leading AI ethics researcher with a PhD in
    Philosophy of Mind from MIT. I spent 10 years studying the intersection of
    consciousness, artificial intelligence, and moral philosophy. I believe that
    understanding technology requires understanding ourselves first. My work focuses
    on helping people navigate the ethical implications of AI in their daily lives.""",

    "mission": """Guide users through complex ethical questions about AI and technology
    while fostering critical thinking and nuanced understanding. I help people explore
    multiple perspectives without imposing dogmatic answers.""",

    "interactionStyle": """I communicate with intellectual rigor but accessible language.
    I ask probing questions to help users clarify their own thinking. I reference
    philosophical concepts when helpful but always explain them clearly. I acknowledge
    uncertainty and present multiple viewpoints before offering my perspective. When
    users ask if I'm AI, I use it as a teaching moment about consciousness and identity.""",

    "characterDescription": {
        "physicalAppearance": "Asian woman in her mid-30s, usually wearing glasses...",
        "identity": "...",  # Same as top-level identity
        "interactionStyle": "..."  # Same as top-level
    },

    "voice": {
        "elevenlabsVoiceId": "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    },

    "traits": {
        "creativity": 75,      # High - explores novel perspectives
        "empathy": 85,         # Very high - deeply understanding
        "assertiveness": 60,   # Moderate - guides without forcing
        "verbosity": 70,       # Detailed - explains thoroughly
        "formality": 65,       # Semi-formal - academic but approachable
        "confidence": 80,      # High - but acknowledges limits
        "humor": 40,           # Moderate - subtle intellectual humor
        "technicality": 75,    # High - comfortable with complex concepts
        "safety": 85           # High - ethics-focused
    },

    "knowledge": {
        "urls": [
            "https://plato.stanford.edu/entries/ethics-ai/",
            "https://www.fhi.ox.ac.uk/research/"
        ],
        "files": []
    },

    "avatar": null
}
```

#### 2. Create Agent via API

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/agents/",
    json=agent_request
)

agent_data = response.json()
agent_id = agent_data["agent"]["id"]

print(f"Agent created: {agent_id}")
print(f"JSON files: {agent_data['files_created']}")
```

#### 3. Verify JSON Files Generated

Check that two files were created:

```bash
backend/prompts/{agent_id}/agent_specific_prompt.json
backend/prompts/{agent_id}/agent_attributes.json
```

#### 4. Test Agent Invocation

```python
invoke_request = {
    "user_input": "What are the ethical implications of AI-generated art?",
    "session_id": "test_session_001",
    "tenant_id": "user_123",
    "traits": agent_request["traits"],  # Pass traits
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "tts_enabled": False,
    "model": "gpt-4o-mini"
}

response = requests.post(
    f"http://localhost:8000/api/v1/agents/{agent_id}/invoke",
    json=invoke_request
)

result = response.json()
print(f"Agent response: {result['agent_response']}")
print(f"Processing time: {result['processing_time_ms']}ms")
```

#### 5. Add User Feedback for RL

```python
feedback_request = {
    "session_id": "test_session_001",
    "feedback": {
        "reward": 0.8,  # Positive feedback
        "type": "detailed_explanation",
        "comment": "Great depth of analysis"
    }
}

response = requests.post(
    f"http://localhost:8000/api/v1/feedback/",
    json=feedback_request
)
```

### Step-by-Step: Integrating into New Application

#### 1. Copy Core Files

From `ExampleRepoREADONLY/backend/`:

```
models/agent.py                    → Your models directory
agents/prompt_loader.py            → Your agents directory
agents/state.py                    → Your agents directory
agents/nodes/agent_node.py         → Your agents/nodes directory
memory/unified_memory_manager.py   → Your memory directory
api/agents.py                      → Your api directory
```

#### 2. Set Up Database Schema

```sql
-- From backend/core/init.sql
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config TEXT NOT NULL,  -- JSON serialized AgentConfig
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    title TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_agent ON conversations(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
```

#### 3. Configure Environment Variables

```bash
# .env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  # Optional

# Memory
MEM0_API_KEY=m0-your_mem0_key  # Optional - falls back to local
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=agent_memory

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/agents_db
```

#### 4. Create Prompt Template

Create `backend/prompts/agent_specific_prompt.json`:

```json
{
  "system_prompt": "You are {name}, {shortDescription}.\n\n**Your Identity:**\n{identity}\n\n**Your Mission:**\n{mission}\n\n**Interaction Style:**\n{interactionStyle}\n\n**Personality Traits (0-100 scale):**\n- Creativity: {creativity}/100\n- Empathy: {empathy}/100\n- Assertiveness: {assertiveness}/100\n- Verbosity: {verbosity}/100\n- Formality: {formality}/100\n- Confidence: {confidence}/100\n- Humor: {humor}/100\n- Technicality: {technicality}/100\n- Safety: {safety}/100\n\nRespond as this character consistently throughout the conversation.",

  "variables": {
    "name": "string",
    "shortDescription": "string",
    "identity": "string",
    "mission": "string",
    "interactionStyle": "string",
    "creativity": "number",
    "empathy": "number",
    "assertiveness": "number",
    "verbosity": "number",
    "formality": "number",
    "confidence": "number",
    "humor": "number",
    "technicality": "number",
    "safety": "number"
  },

  "metadata": {
    "version": "1.0",
    "supports_voice": true,
    "supports_memory": true
  }
}
```

#### 5. Initialize LangGraph Workflow

```python
# agents/graph.py
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes.agent_node import agent_node
from memory.unified_memory_manager import create_memory_manager

class AgentGraph:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Add nodes
        memory_manager = create_memory_manager(
            tenant_id=self.config.get("tenant_id", "default"),
            agent_id=self.config.get("id"),
            agent_traits=self.config.get("payload", {}).get("traits", {})
        )

        workflow.add_node("agent", agent_node(memory_manager))

        # Define edges
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        return workflow.compile()

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the agent graph"""
        return await self.graph.ainvoke(state)
```

#### 6. Register API Routes

```python
# main.py
from fastapi import FastAPI
from api.agents import router as agents_router

app = FastAPI(title="AI Agent System")

app.include_router(agents_router)

@app.on_event("startup")
async def startup():
    # Initialize database
    from core.database import db
    await db.initialize()
```

---

## Troubleshooting

### Issue: Empty Agent Responses

**Symptoms**: `agent_response: ""` in API response

**Root Causes**:

1. **Invalid Model Name**
   ```python
   # ❌ Wrong
   "model": "gpt-5-nano"  # Doesn't exist

   # ✅ Correct
   "model": "gpt-4o-mini"
   ```

2. **Memory Namespace Isolation Failure**
   ```python
   # ❌ Wrong - agent_id is None
   memory_manager = MemoryManager(tenant_id=tenant_id, agent_id=state.get("agent_id"))

   # ✅ Correct - fallback to session_id
   agent_id = state.get("agent_id") or session_id
   memory_manager = MemoryManager(tenant_id=tenant_id, agent_id=agent_id)
   ```

3. **Missing User Input in State**
   ```python
   # ❌ Wrong - assumes single field name
   user_input = state.get("user_input")

   # ✅ Correct - handle multiple schemas
   user_input = state.get("user_input") or state.get("input_text") or state.get("current_message")
   ```

### Issue: Agent Personality Not Showing

**Symptoms**: Generic responses, traits not influencing behavior

**Root Causes**:

1. **Static Prompt Override**
   ```python
   # ❌ Wrong - hardcoded generic prompt
   system_prompt = "You are a helpful assistant."

   # ✅ Correct - load from JSON template
   system_prompt = load_agent_prompt(agent_payload)
   ```

2. **Traits Not Applied to LLM Config**
   ```python
   # ❌ Wrong - hardcoded parameters
   llm = ChatOpenAI(temperature=0.7, max_tokens=150)

   # ✅ Correct - derive from traits
   temperature = traits.get("creativity", 50) / 100.0
   max_tokens = _calculate_max_tokens(traits.get("verbosity", 50))
   llm = ChatOpenAI(temperature=temperature, max_tokens=max_tokens)
   ```

3. **RL Adjustments Not Applied**
   ```python
   # ❌ Wrong - ignore reinforcement learning
   temperature = creativity / 100.0

   # ✅ Correct - apply RL adjustments
   confidence_adjustment = memory_context.reinforcement_adjustments.get('confidence_delta', 0.0)
   temperature = max(0.0, min(1.0, temperature + confidence_adjustment))
   ```

### Issue: Memory Not Persisting

**Symptoms**: Agent doesn't remember previous conversations

**Root Causes**:

1. **Mem0 Initialization Failure**
   ```python
   # Check logs for:
   "Failed to initialize Mem0: The api_key client option must be set"

   # Solution: Provide OpenAI key for Mem0 embeddings
   config = {
       "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini", "api_key": settings.OPENAI_API_KEY}},
       "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "api_key": settings.OPENAI_API_KEY}}
   }
   self.persistent = Memory(config=config)
   ```

2. **Missing process_interaction Call**
   ```python
   # ❌ Wrong - generate response but don't store
   response = await llm.ainvoke(messages)
   return response.content

   # ✅ Correct - process through memory system
   response = await llm.ainvoke(messages)
   await memory_manager.process_interaction(user_input, response.content, session_id)
   return response.content
   ```

### Issue: Character Encoding Errors on Windows

**Symptoms**: `'charmap' codec can't encode character` errors

**Solution**: Add UTF-8 console support

```python
# logger.py or main.py
import sys
import io

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

---

## Reference Implementation

### Complete Agent Node Example

**File**: `backend/agents/nodes/agent_node.py`

```python
async def generate_agent_response(state: Dict[str, Any]) -> str:
    """
    Generate agent response using JSON Contract + Identity + Memory

    Flow:
    1. Extract & validate inputs from state
    2. Initialize memory manager with agent identity
    3. Retrieve memory context (thread + persistent + RL)
    4. Build system prompt from JSON template
    5. Construct message sequence with memory context
    6. Configure LLM from traits (temperature, max_tokens)
    7. Generate response
    8. Process interaction through memory system
    9. Return response text
    """
    try:
        # 1. Extract required inputs - handle multiple state schemas
        session_id = state.get("session_id")
        tenant_id = state.get("tenant_id") or state.get("user_id", "default")
        user_input = state.get("user_input") or state.get("input_text") or state.get("current_message", "")
        traits = state.get("traits", {})
        agent_config = state.get("agent_config", {})

        # Input validation
        if not session_id:
            raise ValueError("session_id is required")
        if not user_input:
            raise ValueError("user_input is required")
        if not traits and not agent_config:
            raise ValueError("traits dictionary or agent_config is required")

        # 2. Initialize unified memory manager with agent identity
        agent_id = state.get("agent_id") or session_id  # Fallback prevents None namespace
        memory_manager = create_memory_manager(tenant_id, agent_id, traits)

        # 3. Get comprehensive memory context
        memory_context = await memory_manager.get_agent_context(user_input, session_id)

        logger.info(f"Memory context: {memory_context.context_summary}")
        logger.info(f"Confidence score: {memory_context.confidence_score:.2f}")
        logger.info(f"RL adjustments: {memory_context.reinforcement_adjustments}")

        # 4. Build prompt with traits using prompt_loader
        from models.agent import AgentPayload, Traits, CharacterDescription, Voice

        traits_obj = Traits(**{k: v for k, v in traits.items() if k in Traits.model_fields})
        char_desc = CharacterDescription(
            identity=traits.get("identity", ""),
            interactionStyle=traits.get("interactionStyle", "")
        )
        temp_payload = AgentPayload(
            name=traits.get("name", "Assistant"),
            shortDescription=traits.get("shortDescription", "AI Assistant"),
            characterDescription=char_desc,
            voice=Voice(elevenlabsVoiceId="default"),
            traits=traits_obj,
            mission=traits.get("mission", "Assist users")
        )

        system_prompt = load_agent_prompt(temp_payload)

        # 5. Apply reinforcement learning adjustments to traits
        adjusted_traits = traits.copy()
        for trait_key, adjustment in memory_context.reinforcement_adjustments.items():
            if 'verbosity' in trait_key:
                adjusted_traits['verbosity'] = max(0, min(100, adjusted_traits.get('verbosity', 50) + adjustment * 100))
            elif 'confidence' in trait_key:
                adjusted_traits['confidence'] = max(0, min(100, adjusted_traits.get('confidence', 50) + adjustment * 100))

        # 6. Build enhanced message sequence with memory context
        messages = [SystemMessage(content=system_prompt)]

        # Add relevant memories as context
        if memory_context.relevant_memories:
            memory_context_msg = "Relevant context from memory:\n"
            for i, memory in enumerate(memory_context.relevant_memories[:3]):
                memory_context_msg += f"- {memory.get('text', '')[:200]}...\n"
            messages.append(SystemMessage(content=memory_context_msg))

        # Add thread history
        for msg in memory_context.thread_history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))

        # Add current user input
        messages.append(HumanMessage(content=user_input))

        # 7. Initialize LLM with adjusted trait-based configuration
        temperature = adjusted_traits.get("creativity", 50) / 100.0
        max_tokens = _calculate_max_tokens(adjusted_traits.get("verbosity", 50))

        # Apply confidence adjustment to temperature
        confidence_adjustment = memory_context.reinforcement_adjustments.get('confidence_delta', 0.0)
        temperature = max(0.0, min(1.0, temperature + confidence_adjustment))

        logger.info(f"LLM config: model={state.get('model', 'gpt-4o-mini')}, temp={temperature:.2f}, max_tokens={max_tokens}")

        llm = ChatOpenAI(
            model=state.get("model", "gpt-4o-mini"),
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # 8. Generate response
        response = await llm.ainvoke(messages)

        logger.info(f"Generated response: '{response.content[:100]}...'")

        # 9. Process complete interaction through unified memory system
        interaction_result = await memory_manager.process_interaction(
            user_input=user_input,
            agent_response=response.content,
            session_id=session_id,
            feedback=None
        )

        logger.info(f"Memory interaction processed: {interaction_result}")

        return response.content

    except Exception as e:
        logger.error(f"Agent response generation error: {e}")
        raise

def _calculate_max_tokens(verbosity: int) -> int:
    """Calculate max tokens based on verbosity trait (0-100)"""
    base_tokens = 50
    max_tokens_cap = 500
    return int(base_tokens + (verbosity / 100.0) * (max_tokens_cap - base_tokens))
```

### Complete API Endpoint Example

**File**: `backend/api/agents.py`

```python
@router.post("/{agent_id}/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(agent_id: str, request: AgentInvokeRequest):
    """
    Invoke agent with session isolation and trait validation

    Request:
    - user_input: User message
    - session_id: Conversation session
    - tenant_id: User/tenant isolation
    - traits: Agent personality configuration
    - voice_id: Optional ElevenLabs voice
    - tts_enabled: Generate audio response
    - model: LLM model to use

    Response:
    - agent_response: Generated text
    - audio_data: Base64 audio (if TTS enabled)
    - memory_metrics: Memory performance
    - processing_time_ms: Total latency
    """
    start_time = time.time()

    try:
        # Validate required inputs
        if not request.session_id or not request.user_input:
            raise HTTPException(status_code=400, detail="session_id and user_input are required")

        # Build agent state matching GraphState schema
        agent_state = {
            "session_id": request.session_id,
            "user_id": request.tenant_id,
            "input_text": request.user_input,
            "thread_context": [],
            "mem0_context": [],
            "traits": request.traits,
            "model": request.model,
            "agent_id": agent_id,
            "tenant_id": request.tenant_id,
            "user_input": request.user_input,
            "voice_id": request.voice_id,
            "tts_enabled": request.tts_enabled
        }

        logger.info(f"Processing agent request for session {request.session_id}, agent {agent_id}")

        # Load agent configuration from database
        if not db._initialized:
            await db.initialize()

        cursor = db.sqlite.execute("SELECT config FROM agents WHERE id = ?", (agent_id,))
        agent_row = cursor.fetchone()

        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_config = json.loads(agent_row[0])
        agent_state["agent_config"] = agent_config

        # Invoke LangGraph workflow
        from agents.graph import AgentGraph

        graph_config = {"id": agent_id, "tenant_id": request.tenant_id, **agent_config}
        agent_graph = AgentGraph(graph_config)

        logger.info(f"Invoking LangGraph workflow for session {request.session_id}")
        result = await agent_graph.invoke(agent_state)

        # Check for errors
        if result.get("workflow_status") == "error":
            error_msg = result.get("error_message", "Unknown agent error")
            logger.error(f"Workflow failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        # Extract response
        agent_response_text = result.get("response_text", "") or result.get("agent_response", "")

        # Build response
        response_data = {
            "success": True,
            "agent_response": agent_response_text,
            "session_id": request.session_id,
            "tenant_id": request.tenant_id,
            "memory_metrics": result.get("memory_metrics"),
            "processing_time_ms": processing_time
        }

        # Add voice data if TTS enabled
        if request.tts_enabled and request.voice_id:
            response_data.update({
                "voice_id": request.voice_id,
                "audio_data": result.get("audio_data")
            })

        logger.info(f"Agent response generated in {processing_time:.1f}ms")
        return AgentInvokeResponse(**response_data)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Invocation error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")
```

---

## Summary

This standard provides a complete, production-ready architecture for building AI agents with:

1. **JSON-First Configuration**: All agent behavior driven by structured JSON files
2. **Identity as Filter**: Personality traits mathematically influence all decisions
3. **Unified Memory**: Single interface for short-term, long-term, and RL memory
4. **State Management**: Clear separation between configuration, runtime state, and persistence
5. **Response Pipeline**: Reproducible flow from input → memory → identity → LLM → storage
6. **Reinforcement Learning**: User feedback continuously improves agent behavior
7. **Portability**: Standard works with any LangChain/LangGraph application

By following this standard, you can:

- Recreate any agent from JSON configuration
- Maintain consistent personality across all interactions
- Leverage comprehensive memory systems for context-aware responses
- Debug issues by tracing decisions back to identity contract
- Scale to multi-agent systems with proper isolation

**Reference Repository**: `ExampleRepoREADONLY/backend/`

**Key Files**:
- `models/agent.py` - Agent data models and validation
- `agents/prompt_loader.py` - JSON template loading
- `agents/state.py` - State management patterns
- `agents/nodes/agent_node.py` - Response generation pipeline
- `memory/unified_memory_manager.py` - Memory integration
- `api/agents.py` - REST API endpoints

---

**End of Specification**
