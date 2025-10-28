#!/usr/bin/env python
"""
Test FastAPI BackgroundTasks with async functions
This test verifies whether FastAPI BackgroundTasks can execute async functions
"""
import asyncio
import time
from fastapi import FastAPI, BackgroundTasks
from fastapi.testclient import TestClient

app = FastAPI()

# Track execution
execution_log = []

async def async_background_task(task_id: str, message: str):
    """Async background task to test"""
    execution_log.append(f"START:{task_id}")
    print(f"[ASYNC TASK {task_id}] Starting: {message}")
    await asyncio.sleep(0.5)  # Simulate async work
    print(f"[ASYNC TASK {task_id}] Completed")
    execution_log.append(f"END:{task_id}")

@app.post("/test-async-background")
async def test_async_background(background_tasks: BackgroundTasks):
    """Endpoint that adds async background task"""
    print("[ENDPOINT] Adding async background task...")
    background_tasks.add_task(
        async_background_task,
        task_id="test-1",
        message="Testing async in BackgroundTasks"
    )
    print("[ENDPOINT] Background task added, returning response")
    return {"status": "task_scheduled"}

if __name__ == "__main__":
    print("=" * 80)
    print("Testing FastAPI BackgroundTasks with async functions")
    print("=" * 80)

    # Create test client
    client = TestClient(app)

    # Clear log
    execution_log.clear()

    # Make request
    print("\n[TEST] Making POST request...")
    response = client.post("/test-async-background")
    print(f"[TEST] Response: {response.json()}")

    # Give background task time to execute
    print("\n[TEST] Waiting for background task to complete...")
    time.sleep(2)

    # Check execution log
    print("\n[TEST] Execution log:")
    for entry in execution_log:
        print(f"  - {entry}")

    # Verify
    print("\n" + "=" * 80)
    if "START:test-1" in execution_log and "END:test-1" in execution_log:
        print("✅ SUCCESS: Async background task executed successfully!")
        print("   FastAPI BackgroundTasks DOES support async functions.")
    else:
        print("❌ FAILURE: Async background task did NOT execute!")
        print("   FastAPI BackgroundTasks may NOT support async functions.")
        print(f"   Expected: ['START:test-1', 'END:test-1']")
        print(f"   Got: {execution_log}")
    print("=" * 80)
