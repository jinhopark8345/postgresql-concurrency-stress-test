# worker.py
import asyncio
import os
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func
import redis.asyncio as aioredis
from redis.exceptions import ResponseError
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# --- Config ---
DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
    f"@localhost:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
)
REDIS_URL = "redis://localhost"
REDIS_STREAM_KEY = "logs_stream"
REDIS_GROUP = "log_consumers"
REDIS_CONSUMER_NAME = os.getenv("REDIS_CONSUMER_NAME", "log_worker")
NUM_WORKERS = int(os.getenv("NUM_WORKERS", 10))

# --- DB Setup ---
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

# --- Redis Setup ---
redis_client = aioredis.Redis.from_url(REDIS_URL)

# --- Model ---
class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Worker ---
async def redis_worker(name: str):
    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=REDIS_GROUP,
                consumername=name,
                streams={REDIS_STREAM_KEY: '>'},
                count=100,
                block=1000
            )
            if not results:
                continue

            logs_to_insert = []
            msg_ids = []

            for stream, messages in results:
                for msg_id, msg_data in messages:
                    try:
                        raw = msg_data[b"data"]
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        logs_to_insert.append(Log(message=raw))
                        msg_ids.append(msg_id)
                    except Exception as e:
                        logger.warning(f"[{name}] Failed to parse message {msg_id}: {e}")

            async with AsyncSessionLocal() as db:
                try:
                    db.add_all(logs_to_insert)
                    await db.commit()
                    await redis_client.xack(REDIS_STREAM_KEY, REDIS_GROUP, *msg_ids)
                except Exception as e:
                    logger.error(f"[{name}] DB insert failed: {e}")
                    await db.rollback()
        except Exception as e:
            logger.error(f"[{name}] Redis error: {e}")
            await asyncio.sleep(1)

# --- Main Runner ---
async def main():
    try:
        await redis_client.xgroup_create(
            name=REDIS_STREAM_KEY,
            groupname=REDIS_GROUP,
            id="0",
            mkstream=True
        )
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    tasks = [redis_worker(f"{REDIS_CONSUMER_NAME}_{i}") for i in range(NUM_WORKERS)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
