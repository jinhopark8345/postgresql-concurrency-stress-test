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

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
    f"@localhost:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
)

logger.info(f'{DATABASE_URL=}')  # Debugging line to check the DATABASE_URL
# DATABASE_URL = "postgresql+psycopg2://rDGJeEDqAz:XsPQhCoEfOQZueDjsILetLDUvbvSxAMnrVtgVZpmdcSssUgbvs@localhost:5455/default_db"
# print(f'{DATABASE_URL=}')  # Debugging line to check the DATABASE_URL

# pool_size=50: Number of connections kept open
# max_overflow=100: How many additional "overflow" connections can be opened
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=50,
    max_overflow=100,
)

SessionLocal = sessionmaker(bind=engine)
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

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/write")
def write_log(input: LogInput, db: Session = Depends(get_db)):
    db.add(Log(message=input.message))
    db.commit()
    return {"status": "ok"}

@app.get("/messages")
def read_logs(limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(Log).order_by(Log.id.desc()).limit(limit).all()
    return logs
