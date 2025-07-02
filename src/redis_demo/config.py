import os
from dotenv import load_dotenv
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

# DB
DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
    f"@postgres:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
)
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=50, max_overflow=20)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

# Redis
REDIS_URL = "redis://redis"
redis_client = aioredis.Redis.from_url(REDIS_URL)

# Redis stream settings
REDIS_STREAM_KEY = "logs_stream"
REDIS_GROUP = "log_consumers"
REDIS_CONSUMER_NAME = os.getenv("REDIS_CONSUMER_NAME", "log_worker")
NUM_WORKERS = int(os.getenv("NUM_WORKERS", 10))
