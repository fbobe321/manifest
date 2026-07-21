"""SQLite engine/session setup.

Notes for the hardened (read-only root FS) deployment:
* The database file lives under /app/data, the only writable host mount.
* `temp_store=MEMORY` keeps SQLite temp/journal scratch off the read-only
  root filesystem, avoiding writes outside the mounted volume.
"""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


def _sqlite_file_path(url: str) -> Path | None:
    """Extract the on-disk path from a sqlite:/// URL, if any."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    raw = url[len(prefix):]
    # A leading slash here means an absolute path (URL had four slashes).
    return Path(raw)


# Ensure the parent directory of the DB file exists (local/dev convenience).
_db_path = _sqlite_file_path(settings.database_url)
if _db_path is not None:
    _db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models so they register on the metadata before create_all.
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
