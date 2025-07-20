import asyncio
import json
from time import time_ns  


import aiohttp
from loguru import logger
from redis.exceptions import ResponseError

from redis_demo.config import (
    NUM_WORKERS,
    REDIS_CONSUMER_NAME,
    REDIS_GROUP,
    REDIS_STREAM_KEY,
    redis_client,
)

BATCH_SIZE = 100
LOKI_URL = "http://loki:3100/loki/api/v1/push"  # Loki URL inside Docker network


async def push_to_loki(logs):
    streams = [
        {
            "stream": {"job": "log_worker"},
            "values": [[str(time_ns()), log] for log in logs],
        }
    ]
    async with aiohttp.ClientSession() as session:
        async with session.post(LOKI_URL, json={"streams": streams}) as resp:
            if resp.status != 204:
                text = await resp.text()
                logger.error(f"Failed to push to Loki: {resp.status} {text}")


async def redis_worker(name: str):
    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=REDIS_GROUP,
                consumername=name,
                streams={REDIS_STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=1000,  # ms
            )
            if not results:
                continue

            logs = []
            msg_ids = []

            for _, messages in results:
                for msg_id, msg_data in messages:
                    try:
                        raw = msg_data[b"data"].decode()
                        logs.append(raw)
                        msg_ids.append(msg_id)
                    except Exception as e:
                        logger.warning(f"[{name}] Bad msg {msg_id}: {e}")

            if logs:
                await push_to_loki(logs)
                await redis_client.xack(REDIS_STREAM_KEY, REDIS_GROUP, *msg_ids)

        except Exception as e:
            logger.error(f"[{name}] Redis error: {e}")
            await asyncio.sleep(1)


async def main():
    try:
        await redis_client.xgroup_create(
            name=REDIS_STREAM_KEY, groupname=REDIS_GROUP, id="0", mkstream=True
        )
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    await asyncio.gather(
        *[redis_worker(f"{REDIS_CONSUMER_NAME}_{i}") for i in range(NUM_WORKERS)]
    )


if __name__ == "__main__":
    asyncio.run(main())
