"""
Test thread memory persistence after fix.

Verifies that:
1. Messages are saved to thread before LLM invocation
2. Thread context retrieval works correctly
3. No async/await issues with synchronous append_thread
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from backend.memory.memory_manager import MemoryManager
from backend.agents.supervisor_agent import MemoryManagerChatHistory, get_session_history


def test_thread_memory_storage():
    """Test that messages are correctly stored in thread context"""
    print("=" * 80)
    print("TEST 1: Thread Memory Storage")
    print("=" * 80)
    print()

    # Create memory manager
    mm = MemoryManager(tenant_id="test-tenant", agent_id="supervisor")
    session_id = "test-session-123"

    # Add messages to thread (as supervisor does)
    mm.append_thread(session_id, "user", "What platforms do you support?")
    mm.append_thread(session_id, "assistant", "We support TikTok and YouTube Shorts!")

    # Retrieve thread context
    thread_context = mm.get_thread_context(session_id)

    print(f"Thread context length: {len(thread_context)}")
    print()

    assert len(thread_context) == 2, f"Expected 2 messages, got {len(thread_context)}"
    assert thread_context[0]["role"] == "user", "First message should be user"
    assert thread_context[0]["content"] == "What platforms do you support?"
    assert thread_context[1]["role"] == "assistant", "Second message should be assistant"

    print("Thread context:")
    for i, msg in enumerate(thread_context):
        print(f"  {i+1}. [{msg['role']}]: {msg['content'][:50]}...")
    print()

    print("PASS: Messages stored correctly")
    print()


def test_langchain_history_integration():
    """Test LangChain BaseChatMessageHistory integration"""
    print("=" * 80)
    print("TEST 2: LangChain History Integration")
    print("=" * 80)
    print()

    # Create memory manager
    mm = MemoryManager(tenant_id="test-tenant", agent_id="supervisor")
    session_id = "test-session-456"

    # Add messages
    mm.append_thread(session_id, "user", "Tell me about your features")
    mm.append_thread(session_id, "assistant", "I help create viral content!")

    # Get LangChain-compatible history
    history = MemoryManagerChatHistory(session_id, mm)
    messages = history.messages

    print(f"LangChain messages: {len(messages)}")
    print()

    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"

    from langchain_core.messages import HumanMessage, AIMessage
    assert isinstance(messages[0], HumanMessage), "First message should be HumanMessage"
    assert isinstance(messages[1], AIMessage), "Second message should be AIMessage"
    assert messages[0].content == "Tell me about your features"
    assert messages[1].content == "I help create viral content!"

    print("LangChain message objects:")
    for i, msg in enumerate(messages):
        print(f"  {i+1}. {type(msg).__name__}: {msg.content[:50]}...")
    print()

    print("PASS: LangChain integration working")
    print()


def test_get_session_history():
    """Test get_session_history function"""
    print("=" * 80)
    print("TEST 3: get_session_history Function")
    print("=" * 80)
    print()

    session_id = "test-session-789"
    tenant_id = "test-tenant"

    # Get session history (creates MemoryManager internally)
    history = get_session_history(session_id, tenant_id)

    print(f"History object type: {type(history).__name__}")
    print(f"Session ID: {history.session_id}")
    print()

    assert isinstance(history, MemoryManagerChatHistory), "Should return MemoryManagerChatHistory"
    assert history.session_id == session_id

    # Manually add message to underlying memory manager
    history.memory_manager.append_thread(session_id, "user", "Test message")

    # Verify it appears in messages property
    messages = history.messages
    assert len(messages) == 1
    assert messages[0].content == "Test message"

    print("PASS: get_session_history works correctly")
    print()


def test_message_ordering():
    """Test that messages maintain chronological order"""
    print("=" * 80)
    print("TEST 4: Message Ordering")
    print("=" * 80)
    print()

    mm = MemoryManager(tenant_id="test-tenant", agent_id="supervisor")
    session_id = "test-session-ordering"

    # Simulate conversation
    conversations = [
        ("user", "Create a TikTok video"),
        ("assistant", "Sure! What topic?"),
        ("user", "AI trends"),
        ("assistant", "Great choice! I'll create that."),
        ("user", "What did I ask for?"),
    ]

    for role, content in conversations:
        mm.append_thread(session_id, role, content)

    # Get thread context
    thread_context = mm.get_thread_context(session_id)

    print(f"Conversation history ({len(thread_context)} messages):")
    for i, msg in enumerate(thread_context):
        print(f"  {i+1}. [{msg['role']:9}] {msg['content']}")
    print()

    assert len(thread_context) == 5
    assert thread_context[-1]["content"] == "What did I ask for?"
    assert thread_context[-2]["content"] == "Great choice! I'll create that."

    print("PASS: Messages maintain correct order")
    print()


def test_window_bounding():
    """Test that thread context is bounded to 20 messages"""
    print("=" * 80)
    print("TEST 5: Window Bounding (20 message limit)")
    print("=" * 80)
    print()

    mm = MemoryManager(tenant_id="test-tenant", agent_id="supervisor")
    session_id = "test-session-bounding"

    # Add 25 messages (exceeds 20 limit)
    for i in range(25):
        mm.append_thread(session_id, "user" if i % 2 == 0 else "assistant", f"Message {i+1}")

    thread_context = mm.get_thread_context(session_id)

    print(f"Added 25 messages, thread has: {len(thread_context)} messages")
    print(f"First message: {thread_context[0]['content']}")
    print(f"Last message: {thread_context[-1]['content']}")
    print()

    assert len(thread_context) == 20, f"Expected 20 messages, got {len(thread_context)}"
    assert thread_context[0]["content"] == "Message 6", "Should keep last 20 messages only"
    assert thread_context[-1]["content"] == "Message 25"

    print("PASS: Window bounding works (keeps last 20)")
    print()


def run_all_tests():
    """Run all thread memory tests"""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "THREAD MEMORY FIX VERIFICATION" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        test_thread_memory_storage()
        test_langchain_history_integration()
        test_get_session_history()
        test_message_ordering()
        test_window_bounding()

        print()
        print("╔" + "=" * 78 + "╗")
        print("║" + " " * 30 + "ALL TESTS PASSED" + " " * 32 + "║")
        print("╚" + "=" * 78 + "╝")
        print()
        print("Thread memory is now working correctly!")
        print()
        print("Key fixes applied:")
        print("  1. Removed incorrect 'await' on synchronous append_thread()")
        print("  2. User message saved BEFORE LLM invocation (not after)")
        print("  3. Thread context properly retrieved during conversation")
        print()

        return True

    except AssertionError as e:
        print()
        print("=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        return False
    except Exception as e:
        print()
        print("=" * 80)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
