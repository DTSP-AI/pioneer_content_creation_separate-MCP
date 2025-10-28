#!/usr/bin/env python
"""Test PostgreSQL connection with completely fresh asyncpg"""
import sys
import asyncio

# Clear any cached modules
if 'asyncpg' in sys.modules:
    del sys.modules['asyncpg']

import asyncpg

async def test():
    print("Testing fresh connection...")
    print(f"asyncpg version: {asyncpg.__version__}")

    try:
        # Test 1: Connect with password
        print("\n[Test 1] Connecting WITH password...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='agentuser',
            password='changeme',
            database='content_agent',
            timeout=5
        )
        print("SUCCESS with password!")
        await conn.close()
        return True
    except Exception as e:
        print(f"FAILED with password: {e}")

    try:
        # Test 2: Connect without password (trust)
        print("\n[Test 2] Connecting WITHOUT password (trust)...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='agentuser',
            database='content_agent',
            timeout=5
        )
        print("SUCCESS without password!")
        await conn.close()
        return True
    except Exception as e:
        print(f"FAILED without password: {e}")

    try:
        # Test 3: Connect using DSN
        print("\n[Test 3] Connecting using DSN...")
        conn = await asyncpg.connect(
            'postgresql://agentuser@localhost:5432/content_agent',
            timeout=5
        )
        print("SUCCESS with DSN!")
        await conn.close()
        return True
    except Exception as e:
        print(f"FAILED with DSN: {e}")

    return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
