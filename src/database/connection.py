from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging
from config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

Base = declarative_base()
metadata = MetaData()

engine = create_engine(
    settings.database_url_sync,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True, 
    echo=settings.APP_ENV == "development",  
    future=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute(f"SET TIME ZONE '{settings.TIMEZONE}'")
    cursor.close()
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Connection checked out from pool")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    return SessionLocal()


def test_connection() -> bool:
    try:
        with get_db() as db:
            result = db.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"----xxx----xxx---x----Database connection failed: {str(e)}---x----xxx----xxx")
        return False


def verify_postgis() -> bool:
    try:
        with get_db() as db:
            result = db.execute("SELECT PostGIS_Version()").scalar()
            logger.info(f"PostGIS version: {result}")
            return True
    except Exception as e:
        logger.error(f"----xxx-xxx--xxx-----PostGIS verification failed: {str(e)}----xxx-xxx--xxx-----")
        return False


try:
    test_connection()
    verify_postgis()
except Exception as e:
    logger.warning(f"Initial database connection check failed: {str(e)}")