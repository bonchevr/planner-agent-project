from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# SQLite requires check_same_thread=False; PostgreSQL does not accept this arg
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,   # discard stale connections before use (fixes Fly proxy drops)
    pool_recycle=300,     # recycle connections after 5 min to avoid idle disconnects
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
