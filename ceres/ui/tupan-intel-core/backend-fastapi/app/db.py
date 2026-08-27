import os
import asyncpg
from typing import Optional

pool: Optional[asyncpg.pool.Pool] = None

async def init_db():
    global pool
    if pool is None:
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise RuntimeError('DATABASE_URL not set')
        pool = await asyncpg.create_pool(DATABASE_URL)

async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None

async def fetch(query: str, *args):
    if pool is None:
        raise RuntimeError('DB pool not initialized')
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query: str, *args):
    if pool is None:
        raise RuntimeError('DB pool not initialized')
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def execute(query: str, *args):
    if pool is None:
        raise RuntimeError('DB pool not initialized')
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)
