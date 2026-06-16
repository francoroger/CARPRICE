"""Engine, sessão e Base do SQLAlchemy 2.0.

SQLite no desenvolvimento (sem subir Postgres), Postgres em produção via DATABASE_URL.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _normaliza_url(url: str) -> str:
    """Ajusta a DATABASE_URL para o SQLAlchemy 2.0.

    Aiven/Heroku entregam 'postgres://…'; o SQLAlchemy 2 exige 'postgresql://'.
    Em Postgres sem sslmode, força 'require' (a Aiven só aceita conexão SSL).
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


DB_URL = _normaliza_url(settings.database_url)

# SQLite precisa de check_same_thread=False para uso com FastAPI/threads do scheduler
connect_args: dict = {}
pool_kwargs: dict = {}
if DB_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Postgres (Aiven): recicla conexões antes do timeout do servidor (evita
    # "SSL connection has been closed unexpectedly" quando o backend fica ocioso).
    pool_kwargs = {"pool_size": 5, "max_overflow": 5, "pool_recycle": 280}

engine = create_engine(
    DB_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
    **pool_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: fornece uma sessão e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
