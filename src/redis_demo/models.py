from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
