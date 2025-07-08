import asyncio
import json

from loguru import logger
from redis.exceptions import ResponseError
from sqlalchemy import insert

from redis_demo.config import (NUM_WORKERS, REDIS_CONSUMER_NAME, REDIS_GROUP,
                               REDIS_STREAM_KEY, AsyncSessionLocal,
                               redis_client)
from redis_demo.models import Log  # NOTE: use full import path

BATCH_SIZE = 100

async def redis_worker(name: str):
    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=REDIS_GROUP,
                consumername=name,
                streams={REDIS_STREAM_KEY: '>'},
                count=BATCH_SIZE,
                block=1000  # ms
            )
            if not results:
                continue

            values_to_insert = []
            msg_ids = []

            for _, messages in results:
                for msg_id, msg_data in messages:
                    try:
                        raw = msg_data[b"data"].decode()
                        values_to_insert.append({"message": raw})
                        msg_ids.append(msg_id)
                    except Exception as e:
                        logger.warning(f"[{name}] Bad msg {msg_id}: {e}")

            # if values_to_insert:
            #     async with AsyncSessionLocal() as db:
            #         try:
            #             stmt = insert(Log).values(values_to_insert)
            #             await db.execute(stmt)
            #             await db.commit()
            #             await redis_client.xack(REDIS_STREAM_KEY, REDIS_GROUP, *msg_ids)
            #         except Exception as e:
            #             logger.error(f"[{name}] DB error: {e}")
            #             await db.rollback()
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
