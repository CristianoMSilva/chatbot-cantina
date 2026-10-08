"""Modelo de dados.

Valores em dinheiro são guardados em centavos (número inteiro) para evitar
os problemas de arredondamento de ponto flutuante em valores monetários.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Responsavel(Base):
    """Pai/mãe/responsável — identificado pelo número de WhatsApp."""

    __tablename__ = "responsaveis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    whatsapp_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    alunos: Mapped[list["Aluno"]] = relationship(back_populates="responsavel", cascade="all, delete-orphan")


class Aluno(Base):
    """Criança/aluno vinculado a um responsável (um responsável pode ter vários)."""

    __tablename__ = "alunos"
    __table_args__ = (
        UniqueConstraint("responsavel_id", "nome", "serie", "turno", name="uq_aluno_por_responsavel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsaveis.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    serie: Mapped[str] = mapped_column(String(50), nullable=True)
    turno: Mapped[str] = mapped_column(String(20), nullable=True)  # "manha" | "tarde"

    # Regra de negócio real da Tia Eleusa: fiado é decidido aluno a aluno, não é uma
    # regra global do sistema.
    pode_fiado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    saldo_centavos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    responsavel: Mapped["Responsavel"] = relationship(back_populates="alunos")
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")


class Produto(Base):
    """Item do cardápio."""

    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    preco_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TipoTransacao(str, enum.Enum):
    CREDITO = "credito"
    CONSUMO = "consumo"


class OrigemTransacao(str, enum.Enum):
    MANUAL = "manual"  # lançado pela tia no painel (MVP)
    PIX_AUTOMATICO = "pix_automatico"  # Fase 2


class Transacao(Base):
    """Extrato do aluno: cada crédito lançado ou consumo debitado."""

    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False, index=True)

    tipo: Mapped[TipoTransacao] = mapped_column(Enum(TipoTransacao), nullable=False)
    origem: Mapped[OrigemTransacao] = mapped_column(Enum(OrigemTransacao), default=OrigemTransacao.MANUAL)

    # Sempre positivo; o sinal (soma ou subtrai do saldo) é decidido pelo `tipo`.
    valor_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    aluno: Mapped["Aluno"] = relationship(back_populates="transacoes")


class EstadoConversa(Base):
    """Estado da conversa no WhatsApp por número de telefone.

    Guarda em que etapa do fluxo (ex: cadastro, menu principal) cada número
    está, pra saber o que fazer com a próxima mensagem que ele mandar.
    """

    __tablename__ = "estados_conversa"

    whatsapp_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    etapa: Mapped[str] = mapped_column(String(50), nullable=False)
    contexto_json: Mapped[str] = mapped_column(Text, default="{}")
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SolicitacaoPagamento(Base):
    """A flag raised when a parent picks "payment" in the bot menu.

    The bot itself never handles the payment — it just lets the staff know
    someone wants to pay, so she can reach out manually (see the ADR about
    deferring automatic Pix). `resolvida=True` once she's taken care of it.
    """

    __tablename__ = "solicitacoes_pagamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsaveis.id"), nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolvida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    responsavel: Mapped["Responsavel"] = relationship()
