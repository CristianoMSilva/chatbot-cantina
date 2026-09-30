"""Financial logic: crediting and debiting a student's balance.

This is the core business rule of the project: whether a student can
consume without balance ("fiado" / running a tab) is decided per student
by the canteen staff (`Aluno.pode_fiado`), not by one global rule.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Aluno, OrigemTransacao, Transacao, TipoTransacao


class InsufficientBalanceError(Exception):
    """Raised when a debit would leave a negative balance and it's not allowed."""

    def __init__(self, aluno_id: int, saldo_centavos: int, valor_centavos: int):
        self.aluno_id = aluno_id
        self.saldo_centavos = saldo_centavos
        self.valor_centavos = valor_centavos
        super().__init__(
            f"Student {aluno_id} has insufficient balance: "
            f"balance={saldo_centavos}, amount={valor_centavos}"
        )


@dataclass
class TransactionResult:
    aluno: Aluno
    transacao: Transacao


def add_credit(
    db: Session,
    aluno: Aluno,
    valor_centavos: int,
    descricao: str | None = None,
) -> TransactionResult:
    """Add credit to a student's balance (e.g. a parent just paid)."""
    aluno.saldo_centavos += valor_centavos

    transacao = Transacao(
        aluno_id=aluno.id,
        tipo=TipoTransacao.CREDITO,
        origem=OrigemTransacao.MANUAL,
        valor_centavos=valor_centavos,
        descricao=descricao,
    )
    db.add(transacao)
    db.commit()
    db.refresh(aluno)
    db.refresh(transacao)

    return TransactionResult(aluno=aluno, transacao=transacao)


def debit_consumption(
    db: Session,
    aluno: Aluno,
    valor_centavos: int,
    descricao: str | None = None,
    forcar: bool = False,
) -> TransactionResult:
    """Debit the price of an item the student just consumed.

    If the resulting balance would go negative and the student is not
    allowed to run a tab (`pode_fiado=False`), this raises
    InsufficientBalanceError — unless `forcar=True`, which is the staff
    explicitly overriding the rule for this one purchase.
    """
    saldo_resultante = aluno.saldo_centavos - valor_centavos

    if saldo_resultante < 0 and not aluno.pode_fiado and not forcar:
        raise InsufficientBalanceError(aluno.id, aluno.saldo_centavos, valor_centavos)

    aluno.saldo_centavos = saldo_resultante

    transacao = Transacao(
        aluno_id=aluno.id,
        tipo=TipoTransacao.CONSUMO,
        origem=OrigemTransacao.MANUAL,
        valor_centavos=valor_centavos,
        descricao=descricao,
    )
    db.add(transacao)
    db.commit()
    db.refresh(aluno)
    db.refresh(transacao)

    return TransactionResult(aluno=aluno, transacao=transacao)
