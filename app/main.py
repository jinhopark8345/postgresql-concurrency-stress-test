# main.py
from fastapi import FastAPI
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.future import select
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from loguru import logger
import json
import redis.asyncio as aioredis

load_dotenv()

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
    f"@postgres:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
)

logger.info(f'{DATABASE_URL=}')

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=50, max_overflow=20)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

REDIS_URL = "redis://redis"
REDIS_STREAM_KEY = "logs_stream"
redis_client = aioredis.Redis.from_url(REDIS_URL)

app = FastAPI()

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LogInput(BaseModel):
    message: dict

class LogOutput(BaseModel):
    id: int
    message: str

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
        result = await db.execute(
            select(Log).order_by(Log.id.desc()).limit(limit)
        )
        rows = result.scalars().all()
        return [{"id": row.id, "message": row.message} for row in rows]
