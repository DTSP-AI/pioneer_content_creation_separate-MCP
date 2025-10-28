#!/usr/bin/env python
"""Test database connection"""
import asyncio
import asyncpg

async def test_connection():
    try:
        print("Testing PostgreSQL connection...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5433,
            user='agentuser',
            password='changeme',
            database='content_agent'
        )
        print("✅ SUCCESS: Connected to PostgreSQL!")

        # Test a simple query
        result = await conn.fetchval('SELECT version();')
        print(f"PostgreSQL version: {result[:50]}...")

        await conn.close()
        print("✅ Connection closed successfully")
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
