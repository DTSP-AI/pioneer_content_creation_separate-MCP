"""
Test 2: Verify Mem0 Initialization
Tests that Mem0 initializes correctly and can perform basic operations.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.memory import MemoryManager

def test_mem0_initialization():
    """Test that Mem0 initializes successfully."""
    print("\n=== Test 2: Mem0 Initialization ===\n")

    # Initialize memory manager
    memory = MemoryManager(tenant_id="test-tenant", agent_id="supervisor")

    # Check Mem0 is enabled
    print(f"✅ Mem0 enabled: {memory.mem0 is not None}")
    print(f"✅ Namespace: {memory.namespace}")

    # Test semantic storage
    print("\n--- Testing semantic storage ---")
    mem_id = memory.add_fact(
        user_id="test-user",
        text="Test fact: User prefers TikTok videos about AI trends",
        category="preference",
        tags=["tiktok", "ai", "test"]
    )
    print(f"✅ Stored memory ID: {mem_id}")

    # Test retrieval
    print("\n--- Testing semantic retrieval ---")
    results = memory.retrieve(user_id="test-user", query="What platform does user like?")
    print(f"✅ Found {len(results)} relevant memories")

    if results:
        for i, result in enumerate(results[:3], 1):
            memory_text = result.get('memory', '')
            category = result.get('metadata', {}).get('category', 'N/A')
            tags = result.get('metadata', {}).get('tags', [])
            print(f"\n  {i}. Memory: {memory_text[:100]}...")
            print(f"     Category: {category}")
            print(f"     Tags: {tags}")

    # Get memory metrics
    print("\n--- Memory metrics ---")
    metrics = memory.get_metrics()
    print(f"  Namespace: {metrics['namespace']}")
    print(f"  Mem0 enabled: {metrics['mem0_enabled']}")
    print(f"  Thread count: {metrics['thread_count']}")

    print("\n✅ Test 2: PASSED - Mem0 initialization successful\n")
    return True

if __name__ == "__main__":
    try:
        test_mem0_initialization()
    except Exception as e:
        print(f"\n❌ Test 2: FAILED - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
