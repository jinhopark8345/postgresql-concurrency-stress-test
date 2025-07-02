import asyncio
import json
from redis.exceptions import ResponseError
from loguru import logger

from redis_demo.config import (
    redis_client, AsyncSessionLocal, REDIS_STREAM_KEY,
    REDIS_GROUP, REDIS_CONSUMER_NAME, NUM_WORKERS
)
from models import Log

async def redis_worker(name: str):
    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=REDIS_GROUP,
                consumername=name,
                streams={REDIS_STREAM_KEY: '>'},
                count=500,
                block=1000
            )
            if not results:
                continue

            logs_to_insert, msg_ids = [], []
            for _, messages in results:
                for msg_id, msg_data in messages:
                    try:
                        raw = msg_data[b"data"].decode()
                        logs_to_insert.append(Log(message=raw))
                        msg_ids.append(msg_id)
                    except Exception as e:
                        logger.warning(f"[{name}] Bad msg {msg_id}: {e}")

            async with AsyncSessionLocal() as db:
                try:
                    db.add_all(logs_to_insert)
                    await db.commit()
                    await redis_client.xack(REDIS_STREAM_KEY, REDIS_GROUP, *msg_ids)
                except Exception as e:
                    logger.error(f"[{name}] DB error: {e}")
                    await db.rollback()
        except Exception as e:
            logger.error(f"[{name}] Redis error: {e}")
            await asyncio.sleep(1)

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

    await asyncio.gather(*[redis_worker(f"{REDIS_CONSUMER_NAME}_{i}") for i in range(NUM_WORKERS)])

if __name__ == "__main__":
    asyncio.run(main())
