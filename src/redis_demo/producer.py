import json
from time import perf_counter

import orjson
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.future import select
from starlette.middleware.base import BaseHTTPMiddleware

from redis_demo.config import REDIS_STREAM_KEY, AsyncSessionLocal, engine, redis_client
from redis_demo.models import Base, Log

app = FastAPI(default_response_class=ORJSONResponse)


class LogInput(BaseModel):
    message: dict


import asyncio

log_buffer = []
buffer_lock = asyncio.Lock()
FLUSH_SIZE = 1000
FLUSH_INTERVAL = 0.1


@app.on_event("startup")
async def start_batch_flusher():
    async def flush_loop():
        while True:
            await asyncio.sleep(FLUSH_INTERVAL)
            async with buffer_lock:
                if log_buffer:
                    pipe = redis_client.pipeline()
                    for msg in log_buffer:
                        pipe.xadd(
                            REDIS_STREAM_KEY,
                            fields={"data": orjson.dumps(msg).decode()},
                            id="*",
                            maxlen=1000000,
                        )
                    await pipe.execute()
                    log_buffer.clear()

    asyncio.create_task(flush_loop())


# @app.post("/write")
# async def write_log(input: LogInput):
#     await redis_client.xadd(
#         REDIS_STREAM_KEY,
#         fields={"data": orjson.dumps(input.message).decode()},
#         id="*",
#         maxlen=1000000
#     )
#     return {"status": "queued"}


@app.post("/write")
async def write_log(input: LogInput):
    async with buffer_lock:
        log_buffer.append(input.message)
        if len(log_buffer) >= FLUSH_SIZE:
            pipe = redis_client.pipeline()
            for msg in log_buffer:
                pipe.xadd(
                    REDIS_STREAM_KEY,
                    fields={"data": orjson.dumps(msg).decode()},
                    id="*",
                    maxlen=1000000,
                )
            await pipe.execute()
            log_buffer.clear()
    return {"status": "queued"}


@app.get("/messages")
async def read_logs(limit: int = 100):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Log).order_by(Log.id.desc()).limit(limit))
        return [
            {"id": row.id, "message": row.message} for row in result.scalars().all()
        ]
