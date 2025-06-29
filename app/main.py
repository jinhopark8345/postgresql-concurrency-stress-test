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
from redis.exceptions import ResponseError
import asyncio

load_dotenv()

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
    f"@localhost:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
)

logger.info(f'{DATABASE_URL=}')  # Debugging line to check the DATABASE_URL

# --- Async SQLAlchemy setup ---
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=50, max_overflow=20)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

# --- Redis Config ---
REDIS_STREAM_KEY = "logs_stream"
REDIS_GROUP = "log_consumers"
REDIS_CONSUMER_NAME = "log_worker"
redis_client = aioredis.Redis.from_url("redis://localhost")

app = FastAPI()

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    # message = Column(JSON)
    message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LogInput(BaseModel):
    message: dict

class LogOutput(BaseModel):
    id: int
    message: str


# --- DB Dependency ---
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# --- Routes ---
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# @app.post("/write")
# async def write_log(input: LogInput, db: AsyncSession = Depends(get_db)):
#     # db.add(Log(message=input.message))
#     serialized_message = json.dumps(input.message, ensure_ascii=False)
#     db.add(Log(message=serialized_message))
#     await db.commit()
#     return {"status": "ok"}

# --- Routes ---
@app.post("/write")
async def write_log(input: LogInput):
    await redis_client.xadd(
        REDIS_STREAM_KEY,
        fields={"data": json.dumps(input.message, ensure_ascii=False)},
        id="*"
    )
    return {"status": "queued"}



# @app.get("/messages")
# async def read_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         Log.__table__.select().order_by(Log.id.desc()).limit(limit)
#     )
#     rows = result.fetchall()
#     return [{"id": row.id, "message": row.message} for row in rows]


@app.get("/messages")
async def read_logs(limit: int = 100):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Log).order_by(Log.id.desc()).limit(limit)
        )
        rows = result.scalars().all()
        return [{"id": row.id, "message": row.message} for row in rows]

# --- Background Task: Redis Stream → DB ---
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        await redis_client.xgroup_create(
            name=REDIS_STREAM_KEY, groupname=REDIS_GROUP, id="0", mkstream=True
        )
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    async def redis_worker():
        while True:
            try:
                results = await redis_client.xreadgroup(
                    groupname=REDIS_GROUP,
                    consumername=REDIS_CONSUMER_NAME,
                    streams={REDIS_STREAM_KEY: '>'},
                    count=100,
                    block=1000  # ms
                )
                if not results:
                    continue

                for stream, messages in results:
                    async with AsyncSessionLocal() as db:
                        for msg_id, msg_data in messages:
                            try:
                                raw = msg_data[b"data"]
                                if isinstance(raw, bytes):
                                    raw = raw.decode()
                                db.add(Log(message=raw))
                                await redis_client.xack(REDIS_STREAM_KEY, REDIS_GROUP, msg_id)
                            except Exception as e:
                                logger.warning(f"Failed to process message {msg_id}: {e}")
                        await db.commit()
            except Exception as e:
                logger.error(f"Redis consumer error: {e}")
                await asyncio.sleep(1)

    asyncio.create_task(redis_worker())
