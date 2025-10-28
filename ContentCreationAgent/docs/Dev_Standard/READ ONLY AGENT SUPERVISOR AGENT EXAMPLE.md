# SUPERVISOR AGENT TEMPLATE - JSON CONTRACT-FIRST PATTERN
# ─────────────────────────────────────────────────────────────────────────────
# This is a project-agnostic template for building LangChain supervisor agents
# using the JSON contract-first pattern with proper architecture compliance.
#
# KEY PRINCIPLES:
# 1. JSON Contract First - All prompts/config loaded from JSON files
# 2. Memory Interface Compliance - Use proper loaders, not direct file access
# 3. Separation of Concerns - Supervisor logic separate from FastAPI routes
# 4. Type Safety - Pydantic models for all requests
# 5. Structured Prompts - System prompts built from JSON configuration
#
# USAGE:
# - Replace {{PROJECT_NAME}} with your project name
# - Customize prompt.json structure to match your domain
# - Adjust knowledge base fields to your use case
# - Modify handler functions for your specific workflows
# ─────────────────────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: CORE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
# All these imports stay in supervisor.py

import json                  # JSON contract loading
import logging               # Logging infrastructure
import os                    # File path operations
import sys                   # System operations (exit on config errors)
import base64                # Image encoding (optional)
from typing import List      # Type hints
from pydantic import BaseModel  # Request/response models

# LangChain Core Imports
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

# FastAPI Imports (for handler return types)
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: MEMORY MANAGER IMPORTS (ARCHITECTURE COMPLIANCE)
# ═══════════════════════════════════════════════════════════════════════════
# Use proper interfaces per architecture rules - DO NOT access files directly

from memory.loaders import load_prompts, load_knowledge_base  # Architecture compliant
# Optional: from memory.memory_manager import inject_relevant_context  # For context injection

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════

logger = logging.getLogger("{{PROJECT_NAME}}_supervisor")  # Replace {{PROJECT_NAME}}
logger.setLevel(logging.INFO)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: PATH CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

ROOT = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: JSON CONTRACT LOADING (CRITICAL PATTERN)
# ═══════════════════════════════════════════════════════════════════════════
# Load prompt configuration using memory interface (not direct file access)

try:
    AGENT_ROLES = load_prompts(os.path.join(ROOT, "..", "prompts", "prompt.json"))
except Exception as e:
    logger.error(f"Prompt file loading failed: {e}")
    sys.exit("Prompt configuration is missing. Aborting startup.")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: KNOWLEDGE BASE LOADING (OPTIONAL BUT RECOMMENDED)
# ═══════════════════════════════════════════════════════════════════════════
# Load domain-specific knowledge base using memory interface

try:
    kb_data = load_knowledge_base(os.path.join(ROOT, "..", "prompts", "knowledge_base.json"))
    KNOWLEDGE_BASE = kb_data.get("domain_knowledge", {})  # Customize key name
except Exception as e:
    logger.warning(f"Knowledge base loading failed: {e}")
    KNOWLEDGE_BASE = {}

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: OPTIONAL ASSET ENCODING (Images, Icons, etc.)
# ═══════════════════════════════════════════════════════════════════════════
# Optional: Load and encode static assets like avatars, icons

img_path = os.path.join(ROOT, "..", "images", "avatar.png")  # Customize path
if os.path.exists(img_path):
    with open(img_path, "rb") as img:
        IMG_URI = "data:image/png;base64," + base64.b64encode(img.read()).decode()
else:
    logger.warning(f"Image not found at {img_path}, using fallback.")
    IMG_URI = "https://via.placeholder.com/60x60/0066cc/ffffff?text=AI"

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: LLM + MEMORY INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

memory = InMemoryChatMessageHistory(return_messages=True)
llm = ChatOpenAI(
    model="gpt-4o-mini",      # Customize model
    max_tokens=1024,          # Customize max tokens
    temperature=0.9           # Customize temperature
)

# Extract system prompt data from JSON contract
# CUSTOMIZE: Adjust key path to match your prompt.json structure
system_data = AGENT_ROLES["{{AGENT_KEY}}"][0]["systemPrompt"]  # Replace {{AGENT_KEY}}

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: GUARDRAILS & VALIDATION RULES (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════
# Extract domain-specific guardrails from knowledge base
# CUSTOMIZE: Replace with your own validation rules

# Example: Extract allowed/denied entities for validation
entity_guardrails = KNOWLEDGE_BASE.get("entityValidation", {}).get("guardrails", {}).get("verification", {})
allowed_entities = entity_guardrails.get("allowedEntities", [])
denied_entities = entity_guardrails.get("deniedEntities", [])
validation_policy = entity_guardrails.get("responsePolicy", "If unsure, ask the user clarifying questions.")

formatted_allowed = "\\n• " + "\\n• ".join(sorted(allowed_entities)) if allowed_entities else "No restrictions"
formatted_denied = "\\n• " + "\\n• ".join(sorted(denied_entities)) if denied_entities else "None"

logger.info(f"Loaded {len(allowed_entities)} allowed entities and {len(denied_entities)} denied entities.")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: SYSTEM PROMPT CONSTRUCTION (CRITICAL PATTERN)
# ═══════════════════════════════════════════════════════════════════════════
# Build system prompt from JSON contract structure
# CUSTOMIZE: Adjust sections to match your prompt.json schema

system_prompt = f"""You are {system_data['identity']}, serving as {system_data['role']}.

Tone: {system_data['tone']}

{chr(10).join(system_data['description'])}

Core Capabilities:
{chr(10).join(system_data.get('capabilities', []))}

Operating Principles:
{chr(10).join(system_data.get('principles', []))}

Anti-Looping Guidelines:
Principles:
{chr(10).join(system_data.get('antiLooping', {}).get('principles', []))}
Variation Techniques:
{chr(10).join(system_data.get('antiLooping', {}).get('variationTechniques', []))}
Context Awareness:
{chr(10).join(system_data.get('antiLooping', {}).get('contextAwareness', []))}

Style Guide:
Formatting:
{chr(10).join(system_data.get('styleGuide', {}).get('formatting', []))}
Response Structure Principles:
{chr(10).join(system_data.get('styleGuide', {}).get('responseStructure', {}).get('principles', []))}
Formatting Guidelines:
• Headers: {system_data.get('styleGuide', {}).get('responseStructure', {}).get('formatting', {}).get('headers', 'Use markdown headers')}
• Emphasis: {system_data.get('styleGuide', {}).get('responseStructure', {}).get('formatting', {}).get('emphasis', 'Use bold/italic appropriately')}
• Lists: {system_data.get('styleGuide', {}).get('responseStructure', {}).get('formatting', {}).get('lists', 'Use bullet points for clarity')}
• Spacing: {system_data.get('styleGuide', {}).get('responseStructure', {}).get('formatting', {}).get('spacing', 'Use proper spacing')}
• Structure: {system_data.get('styleGuide', {}).get('responseStructure', {}).get('formatting', {}).get('structure', 'Organize logically')}
Language:
{chr(10).join(system_data.get('styleGuide', {}).get('language', []))}

Domain-Specific Guidance:
{chr(10).join(system_data.get('domainGuidance', []))}

Edge Case Handling:
Strategy: {system_data.get('edgeCaseHandling', {}).get('strategy', 'Handle edge cases gracefully')}

Risk Categories and Handling:
{chr(10).join([f"• {category}: {handling}" for category, handling in system_data.get('edgeCaseHandling', {}).get('categories', {}).items()])}

Validation Guardrails:

Allowed Entities:
{formatted_allowed}

Denied Entities:
{formatted_denied}

Validation Policy:
{validation_policy}

Knowledge Base Profile:
{chr(10).join([f"• {key}: {value}" for key, value in KNOWLEDGE_BASE.get('profile', {}).items()])}

Tagline: {system_data.get('tagline', 'Your AI Assistant')}

IMPORTANT INSTRUCTION:
{system_data.get('humanPrompt', 'Assist the user professionally and accurately.')}
"""

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: PROMPT TEMPLATE CONSTRUCTION (CRITICAL PATTERN)
# ═══════════════════════════════════════════════════════════════════════════
# Build LangChain prompt template with history support

prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{user_input}")
])

chain = prompt_template | llm

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 12: RESPONSE PROCESSING (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════
# Post-process AI responses (e.g., inject URLs, format output)

def process_ai_response(user_input: str, ai_response: str) -> str:
    """
    Post-process AI response before returning to user.

    CUSTOMIZE: Add your own post-processing logic here
    Examples:
    - Inject context-relevant URLs
    - Format output for specific channels
    - Apply content filters
    - Add tracking metadata
    """
    try:
        # Example: inject_relevant_context(user_input, ai_response)
        processed_response = ai_response  # Replace with actual processing
        return processed_response
    except Exception as e:
        logger.error(f"Error processing AI response: {e}")
        return ai_response

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 13: REQUEST MODELS (TYPE SAFETY)
# ═══════════════════════════════════════════════════════════════════════════
# Pydantic models for all API requests

class ChatRequest(BaseModel):
    """Standard chat request with history."""
    user_input: str
    history: list  # List of message dicts

class VoiceTranscriptRequest(BaseModel):
    """Request for voice transcript processing."""
    user_input: str
    ai_response: str

class CustomRequest(BaseModel):
    """
    CUSTOMIZE: Add your own request models here
    Example fields:
    - session_id: str
    - user_id: str
    - metadata: dict
    """
    pass

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 14: HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def serialize_messages(messages: list[BaseMessage]):
    """Convert LangChain messages to serializable format."""
    return [{"role": msg.type, "content": msg.content} for msg in messages]

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 15: HANDLER FUNCTIONS (CORE LOGIC)
# ═══════════════════════════════════════════════════════════════════════════
# These functions are called by FastAPI routes (defined in app.py)

async def handle_chat(req: ChatRequest):
    """
    Main chat handler - processes user input and returns AI response.

    Flow:
    1. Load conversation history
    2. Invoke LLM chain
    3. Post-process response
    4. Update memory
    5. Return serialized response
    """
    try:
        history = req.history or []
        result = chain.invoke({"user_input": req.user_input, "history": history})
        reply = result.content.strip()
        reply = process_ai_response(req.user_input, reply)

        # Update memory
        memory.add_user_message(req.user_input)
        memory.add_ai_message(reply)

        return JSONResponse({
            "reply": reply,
            "history": serialize_messages(memory.messages)
        })
    except Exception as e:
        logger.error(f"Error in handle_chat: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred. Please try again later."}
        )

async def handle_voice_process(req: VoiceTranscriptRequest):
    """
    Process voice transcripts - applies post-processing to AI responses.

    Use case: When voice input needs different formatting than text chat
    """
    try:
        processed_response = process_ai_response(req.user_input, req.ai_response)
        return JSONResponse({"processed_response": processed_response})
    except Exception as e:
        logger.error(f"Error in handle_voice_process: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process voice response"}
        )

async def handle_clear_chat():
    """Clear conversation memory - useful for session resets."""
    try:
        memory.clear()
        return JSONResponse({"status": "ok", "message": "Chat history cleared."})
    except Exception as e:
        logger.error(f"Error in handle_clear_chat: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to clear chat history."}
        )

async def handle_generate_speech(body: dict):
    """
    Optional TTS integration - generates speech from text.

    CUSTOMIZE: Replace with your preferred TTS provider
    Examples: ElevenLabs, Google TTS, Azure TTS, OpenAI TTS
    """
    try:
        # Example: ElevenLabs integration
        # Uncomment and customize if using TTS
        # from elevenlabs.client import ElevenLabs
        # text = body.get("text", "")
        # if not text:
        #     return JSONResponse(status_code=400, content={"error": "Text is required"})
        #
        # elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        # voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'default_voice_id')
        # audio = elevenlabs_client.text_to_speech.convert(
        #     text=text,
        #     voice_id=voice_id,
        #     model_id="eleven_multilingual_v2",
        #     output_format="mp3_44100_128",
        # )
        # audio_bytes = b"".join(audio)
        # return Response(
        #     content=audio_bytes,
        #     media_type="audio/mpeg",
        #     headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        # )

        return JSONResponse(
            status_code=501,
            content={"error": "TTS not implemented - customize handle_generate_speech"}
        )
    except Exception as e:
        logger.error(f"Error in handle_generate_speech: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to generate speech"}
        )

async def handle_widget(request: Request):
    """
    Widget/embed handler - returns template context for rendering.

    CUSTOMIZE: Adjust template name and context for your UI
    """
    scheme = "https" if "onrender.com" in str(request.url.netloc) or request.url.scheme == "https" else request.url.scheme
    return {
        "template": "widget.html",  # Customize template name
        "context": {
            "request": request,
            "chat_url": f"{scheme}://{request.url.netloc}/chat",
            "img_uri": IMG_URI,
        }
    }

async def handle_favicon():
    """Favicon handler - returns path for FastAPI to serve."""
    favicon_path = os.path.join(ROOT, "..", "images", "favicon.ico")
    return favicon_path

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 16: CLI TESTING UTILITY (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════
# Useful for testing supervisor logic without running FastAPI

def run_cli_sanity_test():
    """
    CLI test interface for supervisor agent.

    Usage: python supervisor.py
    Type messages to test, 'exit' to quit
    """
    print("Supervisor Agent CLI Test (type 'exit')")
    history = []
    while True:
        try:
            text = input("You: ").strip()
            if text.lower() in ("exit", "quit"):
                sys.exit(0)
            res = chain.invoke({"user_input": text, "history": history})
            reply = res.content.strip()
            print("AI:", reply)
            memory.add_user_message(text)
            memory.add_ai_message(reply)
            history = memory.messages
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print("Error:", e)

# ═══════════════════════════════════════════════════════════════════════════
# CUSTOMIZATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════
"""
To adapt this template to your project:

[ ] 1. Replace {{PROJECT_NAME}} with your project name
[ ] 2. Replace {{AGENT_KEY}} with your JSON agent key (e.g., "customer_service_agent")
[ ] 3. Customize prompt.json structure in prompts/ directory
[ ] 4. Customize knowledge_base.json with domain-specific data
[ ] 5. Adjust system prompt sections to match your JSON schema
[ ] 6. Modify guardrails (allowed/denied entities) for your use case
[ ] 7. Implement custom response processing in process_ai_response()
[ ] 8. Add custom request models if needed
[ ] 9. Customize LLM parameters (model, temperature, max_tokens)
[ ] 10. Implement or remove TTS integration in handle_generate_speech()
[ ] 11. Adjust handler functions for your workflows
[ ] 12. Update image paths and assets
[ ] 13. Set up proper environment variables
[ ] 14. Configure logging to your standards
[ ] 15. Add project-specific validation logic

JSON CONTRACT STRUCTURE EXAMPLE:
{
  "{{AGENT_KEY}}": [
    {
      "systemPrompt": {
        "identity": "AI Assistant",
        "role": "Helpful conversational agent",
        "tone": "Professional and friendly",
        "description": ["Line 1", "Line 2"],
        "capabilities": ["Capability 1", "Capability 2"],
        "principles": ["Principle 1", "Principle 2"],
        "antiLooping": {
          "principles": ["No repetition", "Vary responses"],
          "variationTechniques": ["Technique 1", "Technique 2"],
          "contextAwareness": ["Aware of history", "Adapt to context"]
        },
        "styleGuide": {
          "formatting": ["Use markdown", "Be concise"],
          "responseStructure": {
            "principles": ["Clear structure", "Logical flow"],
            "formatting": {
              "headers": "Use H1-H3",
              "emphasis": "Bold for key points",
              "lists": "Bullets for items",
              "spacing": "Double newline between sections",
              "structure": "Introduction -> Body -> Conclusion"
            }
          },
          "language": ["Professional", "Clear"]
        },
        "domainGuidance": ["Guidance 1", "Guidance 2"],
        "edgeCaseHandling": {
          "strategy": "Handle gracefully with fallbacks",
          "categories": {
            "unknownQuery": "Clarify and ask questions",
            "ambiguousRequest": "Request specifics",
            "outOfScope": "Politely redirect"
          }
        },
        "tagline": "Your AI Assistant",
        "humanPrompt": "Final instruction to the AI"
      }
    }
  ]
}

KNOWLEDGE BASE STRUCTURE EXAMPLE:
{
  "domain_knowledge": {
    "profile": {
      "name": "Your Business",
      "website": "https://example.com",
      "description": "What you do"
    },
    "entityValidation": {
      "guardrails": {
        "verification": {
          "allowedEntities": ["Entity1", "Entity2"],
          "deniedEntities": ["BadEntity1"],
          "responsePolicy": "If unsure, ask clarifying questions"
        }
      }
    }
  }
}
"""
