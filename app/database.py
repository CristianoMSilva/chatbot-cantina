"""Configuração da conexão com o banco de dados (SQLAlchemy)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings


def _normalizar_url(url: str) -> str:
    """Hospedagens (ex.: Railway) entregam a URL como "postgresql://...".

    O SQLAlchemy entende esse formato como o driver psycopg2, mas o projeto
    usa o psycopg 3. Trocamos o prefixo para "postgresql+psycopg://".
    """
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


DATABASE_URL = _normalizar_url(settings.database_url)

# connect_args só é necessário para SQLite (usado em dev/testes).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Abre uma conexão por requisição e garante que ela é fechada no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas():
    """Cria as tabelas a partir dos modelos, se ainda não existirem."""
    from app import models  # noqa: F401 (garante que os modelos foram importados)

    Base.metadata.create_all(bind=engine)
