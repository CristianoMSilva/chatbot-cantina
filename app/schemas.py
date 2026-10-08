"""Schemas (Pydantic): formatos de entrada e saída da API.

Os `models.py` são as tabelas do banco. Esses schemas aqui são o que a API
realmente recebe (request) e devolve (response) — nem sempre é a mesma coisa
(por exemplo, o cliente nunca envia o `id`, e a gente nunca devolve tudo que
está salvo no banco sem pensar).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrigemTransacao, TipoTransacao


# ---------- Produto (cardápio) ----------

class ProdutoBase(BaseModel):
    nome: str
    preco_centavos: int = Field(gt=0)


class ProdutoCriar(ProdutoBase):
    """O que a tia envia para cadastrar um novo item do cardápio."""
    pass


class ProdutoAtualizar(BaseModel):
    """Campos que podem ser alterados depois (todos opcionais)."""
    nome: str | None = None
    preco_centavos: int | None = Field(default=None, gt=0)
    disponivel: bool | None = None


class ProdutoOut(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disponivel: bool


# ---------- Aluno ----------

class AlunoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    responsavel_id: int
    nome: str
    serie: str | None
    turno: str | None
    pode_fiado: bool
    saldo_centavos: int


# ---------- Transação (extrato) ----------

class TransacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    tipo: TipoTransacao
    origem: OrigemTransacao
    valor_centavos: int
    descricao: str | None


class LancarCreditoRequest(BaseModel):
    """Usado quando a tia lança um crédito pro aluno (pai pagou)."""
    valor_centavos: int = Field(gt=0)
    descricao: str | None = None


class DebitarConsumoRequest(BaseModel):
    """Usado quando a tia registra que o aluno consumiu algo."""
    valor_centavos: int = Field(gt=0)
    descricao: str | None = None

    # Se o aluno não tem saldo e não pode fiado, a API recusa o débito por
    # padrão. `forcar=True` é a tia dizendo "eu sei, deixa passar mesmo assim".
    forcar: bool = False


# ---------- Payment requests ----------

class ResponsavelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    whatsapp_number: str


class SolicitacaoPagamentoOut(BaseModel):
    """A pending (or resolved) "wants to pay" flag raised from the bot menu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    resolvida: bool
    responsavel: ResponsavelOut
