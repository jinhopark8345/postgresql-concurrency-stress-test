from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.future import select
import json

from redis_demo.config import AsyncSessionLocal, redis_client, REDIS_STREAM_KEY, engine
from redis_demo.models import Log, Base

app = FastAPI()

class LogInput(BaseModel):
    message: dict

@app.post("/write")
async def write_log(input: LogInput):
    await redis_client.xadd(
        REDIS_STREAM_KEY,
        fields={"data": json.dumps(input.message, ensure_ascii=False)},
        id="*"
    )
    return {"status": "queued"}

@app.get("/messages")
async def read_logs(limit: int = 100):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Log).order_by(Log.id.desc()).limit(limit))
        return [{"id": row.id, "message": row.message} for row in result.scalars().all()]
