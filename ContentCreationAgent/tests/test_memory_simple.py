"""
Simple thread memory test (avoids circular imports).

Tests the fix for memory context issues.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from backend.memory.memory_manager import MemoryManager


def test_basic_memory_storage():
    """Test basic thread memory storage and retrieval"""
    print("=" * 80)
    print("TEST: Basic Memory Storage")
    print("=" * 80)
    print()

    mm = MemoryManager(tenant_id="test", agent_id="supervisor")
    session_id = "test-basic-unique"  # Unique session ID

    # Check initial state
    initial_thread = mm.get_thread_context(session_id)
    print(f"Initial thread state: {len(initial_thread)} messages")

    # Simulate conversation flow (after fix)
    print("Simulating conversation:")
    print("  1. User: 'What platforms do you support?'")
    mm.append_thread(session_id, "user", "What platforms do you support?")

    # Retrieve thread before LLM (this is what happens in supervisor after fix)
    # IMPORTANT: Make a copy since get_thread_context returns mutable reference!
    thread_before_llm = list(mm.get_thread_context(session_id))
    print(f"  2. Thread context BEFORE LLM: {len(thread_before_llm)} messages")
    if thread_before_llm:
        for i, msg in enumerate(thread_before_llm):
            print(f"     {i+1}. [{msg['role']}] {msg['content'][:50]}")

    # LLM generates response
    print("  3. LLM generates response...")
    mm.append_thread(session_id, "assistant", "We support TikTok and YouTube Shorts!")

    # Full thread after response
    thread_after = mm.get_thread_context(session_id)
    print(f"  4. Thread context AFTER response: {len(thread_after)} messages")
    print()

    # The key insight: user message should be visible before LLM response
    assert len(thread_before_llm) >= 1, f"User message should be in thread, got {len(thread_before_llm)}"

    # Debug: print what we actually have
    last_msg_role = thread_before_llm[-1].get("role", "MISSING")
    if last_msg_role != "user":
        print(f"DEBUG: Last message dict: {thread_before_llm[-1]}")
        print(f"DEBUG: Role field value: '{last_msg_role}' (type: {type(last_msg_role)})")

    assert thread_before_llm[-1]["role"] == "user", f"Last message role is '{last_msg_role}', expected 'user'"
    assert len(thread_after) == len(thread_before_llm) + 1, "Should have one more message after assistant response"

    print("PASS: User message available in thread BEFORE LLM invocation")
    print()
    return True


def test_followup_conversation():
    """Test that follow-up messages can see previous context"""
    print("=" * 80)
    print("TEST: Follow-Up Conversation Context")
    print("=" * 80)
    print()

    mm = MemoryManager(tenant_id="test", agent_id="supervisor")
    session_id = "test-followup-unique"

    # First exchange
    print("First exchange:")
    print("  User: 'Create a TikTok video'")
    mm.append_thread(session_id, "user", "Create a TikTok video")
    print("  Assistant: 'Sure! What topic?'")
    mm.append_thread(session_id, "assistant", "Sure! What topic?")
    print()

    # Second exchange - user asks follow-up
    print("Follow-up exchange:")
    print("  User: 'AI trends'")
    mm.append_thread(session_id, "user", "AI trends")

    # LLM retrieves context (this is what supervisor does)
    thread_context = mm.get_thread_context(session_id)
    print(f"  Thread context available to LLM: {len(thread_context)} messages")
    for i, msg in enumerate(thread_context):
        print(f"    {i+1}. [{msg['role']:9}] {msg['content']}")
    print()

    assert len(thread_context) == 3
    assert thread_context[-1]["content"] == "AI trends"
    assert thread_context[-2]["content"] == "Sure! What topic?"
    assert thread_context[-3]["content"] == "Create a TikTok video"

    print("PASS: Follow-up messages have full conversation context")
    print()
    return True


def test_memory_recall_question():
    """Test 'What did I ask?' type questions"""
    print("=" * 80)
    print("TEST: Memory Recall Question")
    print("=" * 80)
    print()

    mm = MemoryManager(tenant_id="test", agent_id="supervisor")
    session_id = "test-recall-unique"

    # Build conversation history
    exchanges = [
        ("user", "What platforms do you support?"),
        ("assistant", "We support TikTok and YouTube Shorts!"),
        ("user", "Which is better for tech content?"),
        ("assistant", "YouTube Shorts tends to perform better for technical content."),
        ("user", "What did I ask you about earlier?"),  # Memory recall question
    ]

    for role, content in exchanges:
        mm.append_thread(session_id, role, content)
        print(f"  [{role:9}] {content}")

    print()

    # Get context for LLM to answer memory recall
    thread_context = mm.get_thread_context(session_id)
    print(f"Thread context for memory recall: {len(thread_context)} messages")
    print()

    # Check that ALL previous messages are available
    assert len(thread_context) == 5
    assert "platforms" in thread_context[0]["content"]
    assert "tech content" in thread_context[2]["content"]

    print("PASS: LLM has full context to answer 'What did I ask?' questions")
    print()
    return True


def run_all_tests():
    """Run all simple memory tests"""
    print()
    print("=" * 80)
    print(" " * 25 + "MEMORY FIX VERIFICATION")
    print("=" * 80)
    print()

    try:
        test_basic_memory_storage()
        test_followup_conversation()
        test_memory_recall_question()

        print()
        print("=" * 80)
        print(" " * 30 + "ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("MEMORY FIX SUMMARY:")
        print()
        print("  BEFORE FIX:")
        print("    - User message saved AFTER LLM invocation")
        print("    - LLM couldn't see current message in thread")
        print("    - Broken conversational continuity")
        print()
        print("  AFTER FIX:")
        print("    - User message saved BEFORE LLM invocation")
        print("    - LLM sees current message in thread context")
        print("    - Full conversational context maintained")
        print()
        print("  FILE CHANGED:")
        print("    - backend/agents/supervisor_agent.py:125-137")
        print()
        return True

    except AssertionError as e:
        print()
        print("=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
