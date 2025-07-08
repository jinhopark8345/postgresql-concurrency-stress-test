import json
from time import perf_counter

import orjson
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.future import select
from starlette.middleware.base import BaseHTTPMiddleware

from redis_demo.config import (REDIS_STREAM_KEY, AsyncSessionLocal, engine,
                               redis_client)
from redis_demo.models import Base, Log

app = FastAPI(default_response_class=ORJSONResponse)


class LogInput(BaseModel):
    message: dict

# from fastapi import Request
# from fastapi.responses import HTMLResponse
# from pyinstrument import Profiler


# @app.middleware("http")
# async def profile_request(request: Request, call_next):
#     profiling = request.query_params.get("profile", False)
#     if profiling:
#         profiler = Profiler()
#         profiler.start()

#         response = await call_next(request)  # ❗ Capture response
#         profiler.stop()

#         path = "/app/profile.html"
#         with open(path, "w") as f:
#             f.write(profiler.output_html())

#         return HTMLResponse(content=f"Saved to {path}")

#         # html = profiler.output_html()
#         # return HTMLResponse(content=html, media_type="text/html")  # ❗ Return HTML report

#     else:
#         return await call_next(request)


# @app.post("/write")
# async def write_log(input: LogInput):
#     await redis_client.xadd(
#         REDIS_STREAM_KEY,
#         fields={"data": json.dumps(input.message, ensure_ascii=False)},
#         id="*",
#         maxlen=1000000
#     )
#     return {"status": "queued"}

@app.post("/write")
async def write_log(input: LogInput):
    await redis_client.xadd(
        REDIS_STREAM_KEY,
        fields={"data": orjson.dumps(input.message).decode()},
        id="*",
        maxlen=1000000
    )
    return {"status": "queued"}

@app.get("/messages")
async def read_logs(limit: int = 100):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Log).order_by(Log.id.desc()).limit(limit))
        return [{"id": row.id, "message": row.message} for row in result.scalars().all()]
