from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import DateTime, func
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# DATABASE_URL = (
#     f"postgresql+psycopg2://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
#     f"@localhost:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
# )

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
    f"@localhost:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
)

logger.info(f'{DATABASE_URL=}')  # Debugging line to check the DATABASE_URL
# DATABASE_URL = "postgresql+psycopg2://rDGJeEDqAz:XsPQhCoEfOQZueDjsILetLDUvbvSxAMnrVtgVZpmdcSssUgbvs@localhost:5455/default_db"
# print(f'{DATABASE_URL=}')  # Debugging line to check the DATABASE_URL

# pool_size=50: Number of connections kept open
# max_overflow=100: How many additional "overflow" connections can be opened
# engine = create_engine(
#     DATABASE_URL,
#     pool_pre_ping=True,
#     pool_size=50,
#     max_overflow=100,
# )

# --- Async SQLAlchemy setup ---
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=50,
    max_overflow=100
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LogInput(BaseModel):
    message: dict

class LogOutput(BaseModel):
    id: int
    message: dict


# --- DB Dependency ---
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# --- Routes ---
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/write")
async def write_log(input: LogInput, db: AsyncSession = Depends(get_db)):
    db.add(Log(message=input.message))
    await db.commit()
    return {"status": "ok"}

@app.get("/messages")
async def read_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        Log.__table__.select().order_by(Log.id.desc()).limit(limit)
    )
    rows = result.fetchall()
    return [{"id": row.id, "message": row.message} for row in rows]
