"""Configuração da conexão com o banco de dados (SQLAlchemy)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# connect_args só é necessário para SQLite (usado em dev/testes).
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
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
