"""
Agent Registry

Centralized registry for loading and accessing agent identity contracts (JSON).

This module provides:
1. AgentRegistry class for loading agent configurations
2. Helper functions to access agent metadata, prompts, and capabilities
3. Validation of agent contracts against schema

Usage:
    from backend.agents.registry import AgentRegistry

    # Load all agents
    registry = AgentRegistry()

    # Get specific agent config
    supervisor_config = registry.get_agent("supervisor_agent")
    print(supervisor_config["description"])

    # Get agent prompt template
    prompt = registry.get_prompt_template("supervisor_agent", "system")
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Agent Contract Validation
# =============================================================================

class AgentCapabilities(BaseModel):
    """Agent capabilities schema."""
    llm_model: Optional[str] = None
    memory_aware: Optional[bool] = False
    structured_output: Optional[bool] = False
    cost_tracking: Optional[bool] = False
    multi_tenant: Optional[bool] = False


class AgentContract(BaseModel):
    """
    Agent identity contract schema.

    Defines the structure that all agent JSON configs must follow.
    """
    agent_id: str = Field(description="Unique identifier for the agent")
    agent_name: str = Field(description="Human-readable agent name")
    version: str = Field(description="Agent version (semver)")
    description: str = Field(description="Agent purpose and role")
    role: str = Field(description="Agent role in system (orchestrator, content_generator, platform_publisher)")
    responsibilities: List[str] = Field(description="List of agent responsibilities")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Agent capabilities")
    inputs: Dict[str, List[str]] = Field(default_factory=dict, description="Required and optional inputs")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Output schema")

    class Config:
        extra = "allow"  # Allow additional fields not in schema


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """
    Centralized registry for agent identity contracts.

    Loads all agent JSON configs from backend/agents/prompts/ and provides
    easy access to agent metadata, prompts, and capabilities.
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize Agent Registry.

        Args:
            prompts_dir: Path to prompts directory (defaults to backend/agents/prompts/)
        """
        if prompts_dir is None:
            # Default to backend/agents/prompts/
            current_file = Path(__file__)
            prompts_dir = current_file.parent / "prompts"

        self.prompts_dir = prompts_dir
        self.agents: Dict[str, Dict[str, Any]] = {}
        self._load_agents()

    def _load_agents(self) -> None:
        """Load all agent JSON configs from prompts directory."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            return

        logger.info(f"Loading agent contracts from: {self.prompts_dir}")

        json_files = list(self.prompts_dir.glob("*.json"))

        if not json_files:
            logger.warning(f"No JSON files found in {self.prompts_dir}")
            return

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    agent_config = json.load(f)

                # Validate against schema
                try:
                    AgentContract(**agent_config)
                except ValidationError as e:
                    logger.error(f"Validation failed for {json_file.name}: {e}")
                    continue

                agent_id = agent_config.get("agent_id")
                if agent_id:
                    self.agents[agent_id] = agent_config
                    logger.info(f"Loaded agent: {agent_id} from {json_file.name}")
                else:
                    logger.warning(f"Agent config missing 'agent_id': {json_file.name}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from {json_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {e}")

        logger.info(f"Agent registry initialized with {len(self.agents)} agents")

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent configuration by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent config dict or None if not found
        """
        return self.agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded agent configurations."""
        return self.agents

    def get_agent_ids(self) -> List[str]:
        """Get list of all registered agent IDs."""
        return list(self.agents.keys())

    def get_prompt_template(
        self,
        agent_id: str,
        template_name: str = "system"
    ) -> Optional[str]:
        """
        Get agent prompt template.

        Args:
            agent_id: Agent identifier
            template_name: Template name (e.g., "system", "user")

        Returns:
            Prompt template string or None
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return None

        prompt_template = agent.get("prompt_template", {})

        # Handle both single template and multiple templates
        if isinstance(prompt_template, str):
            return prompt_template
        elif isinstance(prompt_template, dict):
            return prompt_template.get(template_name)

        return None

    def get_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent capabilities.

        Args:
            agent_id: Agent identifier

        Returns:
            Capabilities dict
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {}

        return agent.get("capabilities", {})

    def get_responsibilities(self, agent_id: str) -> List[str]:
        """
        Get agent responsibilities.

        Args:
            agent_id: Agent identifier

        Returns:
            List of responsibilities
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return []

        return agent.get("responsibilities", [])

    def get_tools(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get agent tools configuration.

        Args:
            agent_id: Agent identifier

        Returns:
            List of tool configs
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return []

        return agent.get("tools", [])

    def get_workflow(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent workflow configuration.

        Args:
            agent_id: Agent identifier

        Returns:
            Workflow dict
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {}

        return agent.get("workflow", {})

    def get_platform_requirements(self, agent_id: str) -> Dict[str, Any]:
        """
        Get platform-specific requirements (for platform agents).

        Args:
            agent_id: Agent identifier

        Returns:
            Platform requirements dict
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {}

        return agent.get("platform_requirements", {})

    def validate_agent_inputs(
        self,
        agent_id: str,
        inputs: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate inputs against agent's input schema.

        Args:
            agent_id: Agent identifier
            inputs: Input dict to validate

        Returns:
            Tuple of (is_valid, missing_required_fields)
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return False, [f"Agent {agent_id} not found"]

        input_schema = agent.get("inputs", {})
        required_fields = input_schema.get("required", [])

        missing_fields = []
        for field in required_fields:
            if field not in inputs:
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields

    def get_agent_summary(self, agent_id: str) -> str:
        """
        Get formatted summary of agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Formatted summary string
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return f"Agent {agent_id} not found"

        summary = f"""
Agent: {agent.get('agent_name', 'Unknown')}
ID: {agent.get('agent_id')}
Version: {agent.get('version')}
Role: {agent.get('role')}

Description:
{agent.get('description')}

Responsibilities:
"""
        for i, resp in enumerate(agent.get('responsibilities', []), 1):
            summary += f"{i}. {resp}\n"

        return summary.strip()


# =============================================================================
# Global Registry Instance
# =============================================================================

# Singleton instance
_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """
    Get global agent registry instance (singleton).

    Returns:
        AgentRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


# =============================================================================
# Convenience Functions
# =============================================================================

def get_agent_config(agent_id: str) -> Optional[Dict[str, Any]]:
    """Get agent configuration (convenience function)."""
    registry = get_agent_registry()
    return registry.get_agent(agent_id)


def get_agent_prompt(agent_id: str, template_name: str = "system") -> Optional[str]:
    """Get agent prompt template (convenience function)."""
    registry = get_agent_registry()
    return registry.get_prompt_template(agent_id, template_name)


def list_all_agents() -> List[str]:
    """List all registered agent IDs (convenience function)."""
    registry = get_agent_registry()
    return registry.get_agent_ids()
