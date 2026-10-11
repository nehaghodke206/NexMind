from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

engine_kwargs = {
    "pool_pre_ping": True,
    "echo": (settings.LOG_LEVEL.upper() == "DEBUG"),
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Conservative connection pooling for PostgreSQL
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 1800

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)


# Enable foreign keys for SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
