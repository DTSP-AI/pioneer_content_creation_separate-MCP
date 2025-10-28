#!/usr/bin/env python
"""Test simple PostgreSQL connection without password"""
import asyncio
import asyncpg

async def test():
    try:
        print("Connecting without password...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='agentuser',
            database='content_agent'
            # No password - relying on trust auth
        )
        print("SUCCESS: Connected!")
        result = await conn.fetchval('SELECT 1;')
        print(f"Query result: {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

asyncio.run(test())
