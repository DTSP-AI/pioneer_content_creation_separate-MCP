"""
Test Supervisor Agent Knowledge

Validates that the SupervisorAgent contract contains:
1. Detailed knowledge of sub-agents and their capabilities
2. PiAPI MCP connection information
3. Comprehensive system prompt for chat responses
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import registry directly to avoid circular import
import importlib.util
registry_spec = importlib.util.spec_from_file_location(
    "registry",
    str(Path(__file__).parent.parent / "agents" / "registry.py")
)
registry_module = importlib.util.module_from_spec(registry_spec)
registry_spec.loader.exec_module(registry_module)

get_agent_registry = registry_module.get_agent_registry


def test_supervisor_sub_agent_knowledge():
    """Test that supervisor has detailed knowledge of sub-agents."""
    print("=" * 80)
    print("TEST: Supervisor Sub-Agent Knowledge")
    print("=" * 80)

    registry = get_agent_registry()
    supervisor_config = registry.get_agent("supervisor_agent")

    # Check sub-agents section
    sub_agents = supervisor_config.get("sub_agents", {})

    print(f"\nSub-agents defined: {len(sub_agents)}")

    # Validate ContentCreationAgent
    content_agent = sub_agents.get("content_creation_agent", {})
    assert content_agent, "ContentCreationAgent should be defined"
    assert content_agent.get("role") == "content_generator"
    assert "tools" in content_agent
    assert len(content_agent.get("tools", [])) == 3

    print("✅ ContentCreationAgent knowledge validated")
    print(f"   Tools: {content_agent.get('tools')}")

    # Validate TikTokAgent
    tiktok_agent = sub_agents.get("tiktok_agent", {})
    assert tiktok_agent, "TikTokAgent should be defined"
    assert tiktok_agent.get("role") == "platform_publisher"
    assert "requirements" in tiktok_agent

    print("✅ TikTokAgent knowledge validated")
    print(f"   Video requirements: {tiktok_agent.get('requirements', {}).get('video')}")

    # Validate YouTubeShortsAgent
    youtube_agent = sub_agents.get("youtube_shorts_agent", {})
    assert youtube_agent, "YouTubeShortsAgent should be defined"
    assert youtube_agent.get("role") == "platform_publisher"
    assert "requirements" in youtube_agent

    print("✅ YouTubeShortsAgent knowledge validated")
    print(f"   Video requirements: {youtube_agent.get('requirements', {}).get('video')}")

    print("\n✅ TEST PASSED: Supervisor has comprehensive sub-agent knowledge\n")
    return True


def test_supervisor_piapi_mcp_knowledge():
    """Test that supervisor has PiAPI MCP connection knowledge."""
    print("=" * 80)
    print("TEST: Supervisor PiAPI MCP Knowledge")
    print("=" * 80)

    registry = get_agent_registry()
    supervisor_config = registry.get_agent("supervisor_agent")

    # Check PiAPI MCP knowledge section
    piapi_knowledge = supervisor_config.get("piapi_mcp_knowledge", {})

    assert piapi_knowledge, "PiAPI MCP knowledge should be defined"

    # Validate connection details (updated to FastMCP port 8809)
    assert "connection" in piapi_knowledge
    assert "127.0.0.1:8809" in piapi_knowledge.get("connection", "")

    print(f"✅ Connection: {piapi_knowledge.get('connection')}")

    # Validate protocol
    assert "protocol" in piapi_knowledge
    assert "MCP" in piapi_knowledge.get("protocol", "")

    print(f"✅ Protocol: {piapi_knowledge.get('protocol')}")

    # Validate available models
    models = piapi_knowledge.get("available_models", [])
    assert len(models) > 0, "Should have available models defined"
    assert any("hunyuan" in str(m).lower() for m in models)
    assert any("kling" in str(m).lower() for m in models)

    print(f"✅ Available Models: {len(models)}")
    for model in models:
        print(f"   - {model}")

    # Validate capabilities
    capabilities = piapi_knowledge.get("capabilities", [])
    assert len(capabilities) > 0
    assert any("video generation" in str(c).lower() for c in capabilities)
    assert any("voiceover" in str(c).lower() for c in capabilities)

    print(f"\n✅ Capabilities: {len(capabilities)}")

    # Validate cost estimation
    cost_info = piapi_knowledge.get("cost_estimation", {})
    assert cost_info, "Cost estimation should be provided"

    print(f"✅ Cost Estimation: {cost_info.get('total_per_workflow')}")

    print("\n✅ TEST PASSED: Supervisor has comprehensive PiAPI MCP knowledge\n")
    return True


def test_supervisor_prompt_template():
    """Test that supervisor prompt template is comprehensive."""
    print("=" * 80)
    print("TEST: Supervisor Prompt Template")
    print("=" * 80)

    registry = get_agent_registry()
    supervisor_config = registry.get_agent("supervisor_agent")

    prompt_template = supervisor_config.get("prompt_template", {})
    system_prompt = prompt_template.get("system", "")

    assert len(system_prompt) > 0, "System prompt should exist"

    print(f"System Prompt Length: {len(system_prompt)} characters")

    # Check for key sections
    required_sections = [
        "YOUR ROLE",
        "YOUR CAPABILITIES",
        "YOUR SUB-AGENTS",
        "ContentCreationAgent",
        "TikTokAgent",
        "YouTubeShortsAgent",
        "PiAPI MCP CONNECTION",
        "MEMORY CONTEXT",
        "DECISION PROCESS",
        "CHAT THREAD BEHAVIOR"
    ]

    missing_sections = []
    for section in required_sections:
        if section not in system_prompt:
            missing_sections.append(section)

    if missing_sections:
        print(f"\n❌ Missing sections: {missing_sections}")
        return False

    print("\n✅ All required sections present:")
    for section in required_sections:
        print(f"   - {section}")

    # Check for specific knowledge (updated for FastMCP port 8809)
    checks = [
        ("PiAPI models", lambda: any(model in system_prompt for model in ["hunyuan", "kling", "luma"])),
        ("FastMCP connection", lambda: "127.0.0.1:8809" in system_prompt or "8809" in system_prompt),
        ("Sub-agent tools", lambda: "GoogleSheetsTrendsTool" in system_prompt or "google sheets" in system_prompt.lower()),
        ("Cost estimates", lambda: "$0" in system_prompt and "cost" in system_prompt.lower()),
        ("Chat behavior", lambda: "conversational" in system_prompt.lower()),
    ]

    print("\n✅ Specific knowledge checks:")
    for check_name, check_func in checks:
        if check_func():
            print(f"   ✅ {check_name}")
        else:
            print(f"   ❌ {check_name} - MISSING")
            return False

    print("\n✅ TEST PASSED: Supervisor prompt template is comprehensive\n")
    return True


def test_chat_response_guidelines():
    """Test that supervisor has chat response guidelines."""
    print("=" * 80)
    print("TEST: Chat Response Guidelines")
    print("=" * 80)

    registry = get_agent_registry()
    supervisor_config = registry.get_agent("supervisor_agent")

    system_prompt = supervisor_config.get("prompt_template", {}).get("system", "")

    # Check for chat behavior instructions
    chat_behaviors = [
        "conversational",
        "explain",
        "cost estimate",
        "clarifying questions",
        "reference past campaigns"
    ]

    print("Checking for chat behavior guidelines:")
    for behavior in chat_behaviors:
        if behavior.lower() in system_prompt.lower():
            print(f"   ✅ {behavior}")
        else:
            print(f"   ⚠️  {behavior} - not explicitly mentioned")

    # At minimum, should have CHAT THREAD BEHAVIOR section
    assert "CHAT THREAD BEHAVIOR" in system_prompt, "Should have chat behavior section"

    print("\n✅ TEST PASSED: Chat response guidelines present\n")
    return True


def main():
    """Run all supervisor knowledge tests."""
    print("=" * 80)
    print("SUPERVISOR AGENT KNOWLEDGE TEST SUITE")
    print("=" * 80)

    tests = [
        ("Sub-Agent Knowledge", test_supervisor_sub_agent_knowledge),
        ("PiAPI MCP Knowledge", test_supervisor_piapi_mcp_knowledge),
        ("Prompt Template", test_supervisor_prompt_template),
        ("Chat Response Guidelines", test_chat_response_guidelines),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)

    print(f"\nTotal: {passed_count}/{total} tests passed")

    if passed_count == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
