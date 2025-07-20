import os

import redis.asyncio as aioredis
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Redis
REDIS_URL = "redis://redis"
redis_client = aioredis.Redis.from_url(REDIS_URL)

# Redis stream settings
REDIS_STREAM_KEY = "logs_stream"
REDIS_GROUP = "log_consumers"
REDIS_CONSUMER_NAME = os.getenv("REDIS_CONSUMER_NAME", "log_worker")
NUM_WORKERS = int(os.getenv("NUM_WORKERS", 10))
