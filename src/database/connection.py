from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool, NullPool
from contextlib import contextmanager
from typing import Generator
import logging
from config import settings
from sqlalchemy import text

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

Base = declarative_base()
metadata = MetaData()


def get_database_url():
    """Get database URL with proper SSL settings for Supabase"""
    database_url = settings.database_url_sync
    
    # Add SSL mode for Supabase (cloud PostgreSQL)
    if "supabase" in database_url or "db." in database_url:
        if "sslmode" not in database_url:
            # Add sslmode=require for Supabase
            if "?" in database_url:
                database_url += "&sslmode=require"
            else:
                database_url += "?sslmode=require"
        logger.info("Using Supabase database with SSL")
    
    return database_url


# Choose connection pool based on environment
# For Supabase free tier, use NullPool to avoid connection limits
is_supabase = "supabase" in settings.database_url_sync or "db." in settings.database_url_sync

if is_supabase:
    # Supabase free tier has connection limits, use NullPool
    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,  # Don't keep connections open
        pool_pre_ping=True,
        echo=settings.APP_ENV == "development",
        future=True,
        connect_args={
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
    )
    logger.info("Database engine created with NullPool (for Supabase)")
else:
    # Local development with connection pooling
    engine = create_engine(
        get_database_url(),
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.APP_ENV == "development",
        future=True
    )
    logger.info("Database engine created with QueuePool (for local development)")


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Set timezone on connection"""
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET TIME ZONE '{settings.TIMEZONE}'")
        cursor.close()
        logger.debug("New database connection established with timezone")
    except Exception as e:
        logger.warning(f"Could not set timezone: {e}")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout"""
    logger.debug("Connection checked out from pool")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session context manager"""
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
    """Get a new database session"""
    return SessionLocal()


def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db() as db:
            result = db.execute(text("SELECT 1")).scalar()
            if result == 1:
                logger.info("✅ Database connection successful")
                return True
            return False
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False


def verify_postgis() -> bool:
    """Verify PostGIS extension is enabled"""
    try:
        with get_db() as db:
            result = db.execute(text("SELECT PostGIS_Version()")).scalar()
            if result:
                logger.info(f"✅ PostGIS version: {result}")
                return True
            return False
    except Exception as e:
        logger.error(f"❌ PostGIS verification failed: {str(e)}")
        return False


try:
    if test_connection():
        verify_postgis()
except Exception as e:
    logger.warning(f"Initial database connection check failed: {str(e)}")
    logger.warning("App will continue, but database features may not work")