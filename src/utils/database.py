import os
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker,DeclarativeBase
from src.utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

DATABASE_URL = (
    f"postgresql://"
    f"{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)


engine = create_engine(
    DATABASE_URL,
    pool_size=10,      # 10 persistent connections kept open
    max_overflow=20,   # 20 extra allowed under load
    echo=False         # set True to print raw SQL queries
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass

def get_db():
    """ FastApi dependency - each request gets its own session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    try :
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False