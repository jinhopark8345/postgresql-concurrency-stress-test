from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os

# DATABASE_URL = (
#     f"postgresql://{os.getenv('DATABASE__USERNAME')}:{os.getenv('DATABASE__PASSWORD')}"
#     f"@localhost:{os.getenv('DATABASE__PORT')}/{os.getenv('DATABASE__DB')}"
# )

DATABASE_URL = "postgresql+psycopg2://rDGJeEDqAz:XsPQhCoEfOQZueDjsILetLDUvbvSxAMnrVtgVZpmdcSssUgbvs@localhost:5455/default_db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/write")
def write_log(message: str = "Hello", db: Session = Depends(get_db)):
    db.add(Log(message=message))
    db.commit()
    return {"status": "ok"}
