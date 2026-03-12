from sqlalchemy import create_engine 
from sqlalchemy.ext.declarative import declarative_base 
from sqlalchemy.orm import sessionmaker 
from sqlalchemy.pool import NullPool

DATABASE_URL = "postgresql://postgres:root@localhost:5432/gunadhya_ai_demo"
# DATABASE_URL = "postgresql://postgres:root@localhost:5432/gunadhya_ai_demo"

engine = create_engine(DATABASE_URL, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()