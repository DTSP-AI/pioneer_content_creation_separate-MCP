"""
Test Supervisor Chat Response

Validates that the SupervisorAgent:
1. Responds with conversational messages in chat threads
2. Understands its role and capabilities
3. Has knowledge of PiAPI MCP connection
4. Knows how to coordinate sub-agents
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.state.state_schema import create_initial_workflow_state
from backend.agents.supervisor_agent import supervisor_node

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_supervisor_chat_response():
    """Test that supervisor generates appropriate chat responses."""
    logger.info("=" * 80)
    logger.info("Testing SupervisorAgent Chat Response")
    logger.info("=" * 80)

    # Create initial state
    initial_state = create_initial_workflow_state(
        workflow_id="test_chat_001",
        tenant_id="test_tenant",
        user_id="test_user",
        thread_id="test_thread",
        user_request="Create a TikTok video about AI content creation tips",
        target_platforms=["tiktok"],
        cost_limit_usd=5.0
    )

    logger.info(f"User Request: {initial_state['user_request']}")
    logger.info(f"Target Platforms: {initial_state['target_platforms']}")

    try:
        # Call supervisor node
        logger.info("\nCalling SupervisorAgent...")
        result = await supervisor_node(initial_state)

        logger.info("\n" + "=" * 80)
        logger.info("SUPERVISOR RESPONSE")
        logger.info("=" * 80)

        # Extract chat messages
        messages = result.get("messages", [])

        if messages:
            supervisor_msg = messages[-1]  # Last message should be from supervisor
            logger.info(f"\nRole: {supervisor_msg.get('role')}")
            logger.info(f"Timestamp: {supervisor_msg.get('timestamp')}")
            logger.info(f"Decision: {supervisor_msg.get('decision')}")
            logger.info(f"\nContent:\n{supervisor_msg.get('content')}")
        else:
            logger.warning("No messages found in response!")

        # Validate decision
        decision = result.get("supervisor_decision", {})
        logger.info("\n" + "=" * 80)
        logger.info("DECISION DETAILS")
        logger.info("=" * 80)
        logger.info(f"Action: {decision.get('action')}")
        logger.info(f"Confidence: {decision.get('confidence'):.2f}")
        logger.info(f"Reasoning: {decision.get('reasoning')}")
        logger.info(f"Topic: {decision.get('extracted_topic')}")
        logger.info(f"Audience: {decision.get('target_audience')}")
        logger.info(f"Style: {decision.get('content_style')}")

        # Validate routing
        logger.info("\n" + "=" * 80)
        logger.info("ROUTING DECISION")
        logger.info("=" * 80)
        logger.info(f"Next Phase: {result.get('current_phase')}")
        logger.info(f"Routing Decision: {result.get('routing_decision')}")
        logger.info(f"Cost Check Passed: {result.get('cost_check_passed')}")

        # Assertions
        assert len(messages) > 0, "Supervisor should add message to thread"
        assert messages[-1]["role"] == "supervisor", "Last message should be from supervisor"
        assert len(messages[-1]["content"]) > 0, "Message should have content"
        assert decision.get("action") in ["create_content", "clarify", "reject"], "Valid action required"
        assert 0.0 <= decision.get("confidence", 0.0) <= 1.0, "Confidence should be 0-1"

        logger.info("\n" + "=" * 80)
        logger.info("✅ TEST PASSED: Supervisor chat response validated")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        logger.exception("Full traceback:")
        return False


async def test_supervisor_knowledge():
    """Test that supervisor has knowledge of system capabilities."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing SupervisorAgent Knowledge")
    logger.info("=" * 80)

    try:
        # Load agent contract
        from backend.agents.registry import get_agent_registry
        registry = get_agent_registry()
        supervisor_config = registry.get_agent("supervisor_agent")

        # Check sub-agent knowledge
        sub_agents = supervisor_config.get("sub_agents", {})
        logger.info(f"\nSub-agents defined: {len(sub_agents)}")
        for agent_id, agent_info in sub_agents.items():
            logger.info(f"  - {agent_id}: {agent_info.get('role')}")

        # Check PiAPI MCP knowledge
        piapi_knowledge = supervisor_config.get("piapi_mcp_knowledge", {})
        logger.info(f"\nPiAPI MCP Knowledge:")
        logger.info(f"  Connection: {piapi_knowledge.get('connection')}")
        logger.info(f"  Protocol: {piapi_knowledge.get('protocol')}")
        logger.info(f"  Available Models: {len(piapi_knowledge.get('available_models', []))}")

        # Check prompt template includes sub-agent details
        prompt = supervisor_config.get("prompt_template", {}).get("system", "")
        logger.info(f"\nPrompt Template Length: {len(prompt)} characters")

        # Validate prompt contains key information
        assert "ContentCreationAgent" in prompt, "Prompt should mention ContentCreationAgent"
        assert "TikTokAgent" in prompt or "tiktok_agent" in prompt.lower(), "Prompt should mention TikTok agent"
        assert "YouTubeShortsAgent" in prompt or "youtube" in prompt.lower(), "Prompt should mention YouTube agent"
        assert "PiAPI" in prompt or "piapi" in prompt.lower(), "Prompt should mention PiAPI"
        assert "MCP" in prompt, "Prompt should mention MCP"

        logger.info("\n✅ Supervisor has comprehensive knowledge of:")
        logger.info("  - Sub-agent capabilities and roles")
        logger.info("  - PiAPI MCP connection details")
        logger.info("  - Available video generation models")
        logger.info("  - Platform requirements and workflows")

        logger.info("\n" + "=" * 80)
        logger.info("✅ TEST PASSED: Supervisor knowledge validated")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        logger.exception("Full traceback:")
        return False


async def main():
    """Run all supervisor chat tests."""
    logger.info("=" * 80)
    logger.info("SUPERVISOR CHAT RESPONSE TEST SUITE")
    logger.info("=" * 80)

    tests = [
        ("Chat Response Generation", test_supervisor_chat_response),
        ("System Knowledge", test_supervisor_knowledge),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")

    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)

    logger.info(f"\nTotal: {passed_count}/{total} tests passed")

    if passed_count == total:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
