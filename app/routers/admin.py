"""Admin router: endpoints used by the canteen staff's panel.

Not authenticated yet — for now this only runs locally, on the staff's own
computer. Authentication can be added later if this ever needs to be
reachable from outside.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Aluno, Produto, Responsavel, SolicitacaoPagamento
from app.schemas import (
    AlunoCriarManual,
    AlunoOut,
    DebitarConsumoRequest,
    LancarCreditoRequest,
    ProdutoAtualizar,
    ProdutoCriar,
    ProdutoOut,
    ResponsavelCriar,
    ResponsavelOut,
    SolicitacaoPagamentoOut,
    TransacaoOut,
)
from app.services.financeiro import InsufficientBalanceError, add_credit, debit_consumption

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Products (menu) ----------

@router.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(db: Session = Depends(get_db)):
    return db.execute(select(Produto)).scalars().all()


@router.post("/produtos", response_model=ProdutoOut, status_code=201)
def criar_produto(dados: ProdutoCriar, db: Session = Depends(get_db)):
    produto = Produto(**dados.model_dump())
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.patch("/produtos/{produto_id}", response_model=ProdutoOut)
def atualizar_produto(produto_id: int, dados: ProdutoAtualizar, db: Session = Depends(get_db)):
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Product not found")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)
    return produto


# ---------- Parents (manual registration, Phase A — the bot normally does this) ----------

@router.get("/responsaveis/buscar", response_model=list[ResponsavelOut])
def buscar_responsaveis(nome: str, db: Session = Depends(get_db)):
    """Search parents by (partial) name — used to pick one before adding a child."""
    stmt = select(Responsavel).where(Responsavel.nome.ilike(f"%{nome}%"))
    return db.execute(stmt).scalars().all()


@router.post("/responsaveis", response_model=ResponsavelOut, status_code=201)
def criar_responsavel(dados: ResponsavelCriar, db: Session = Depends(get_db)):
    existente = db.execute(
        select(Responsavel).where(Responsavel.whatsapp_number == dados.whatsapp_number)
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=409, detail="A parent with this WhatsApp number already exists"
        )

    responsavel = Responsavel(**dados.model_dump())
    db.add(responsavel)
    db.commit()
    db.refresh(responsavel)
    return responsavel


@router.post("/responsaveis/{responsavel_id}/alunos", response_model=AlunoOut, status_code=201)
def criar_aluno(responsavel_id: int, dados: AlunoCriarManual, db: Session = Depends(get_db)):
    responsavel = db.get(Responsavel, responsavel_id)
    if responsavel is None:
        raise HTTPException(status_code=404, detail="Parent not found")

    aluno = Aluno(responsavel_id=responsavel_id, **dados.model_dump())
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return aluno


# ---------- Students ----------

@router.get("/alunos/buscar", response_model=list[AlunoOut])
def buscar_alunos(nome: str, db: Session = Depends(get_db)):
    """Search students by (partial) name — used to find one quickly."""
    stmt = select(Aluno).where(Aluno.nome.ilike(f"%{nome}%"))
    return db.execute(stmt).scalars().all()


@router.get("/alunos/{aluno_id}/extrato", response_model=list[TransacaoOut])
def extrato_aluno(aluno_id: int, db: Session = Depends(get_db)):
    aluno = db.get(Aluno, aluno_id)
    if aluno is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return aluno.transacoes


@router.post("/alunos/{aluno_id}/credito", response_model=AlunoOut)
def lancar_credito_endpoint(
    aluno_id: int, dados: LancarCreditoRequest, db: Session = Depends(get_db)
):
    aluno = db.get(Aluno, aluno_id)
    if aluno is None:
        raise HTTPException(status_code=404, detail="Student not found")

    resultado = add_credit(db, aluno, dados.valor_centavos, dados.descricao)
    return resultado.aluno


@router.post("/alunos/{aluno_id}/consumo", response_model=AlunoOut)
def debitar_consumo_endpoint(
    aluno_id: int, dados: DebitarConsumoRequest, db: Session = Depends(get_db)
):
    aluno = db.get(Aluno, aluno_id)
    if aluno is None:
        raise HTTPException(status_code=404, detail="Student not found")

    try:
        resultado = debit_consumption(
            db, aluno, dados.valor_centavos, dados.descricao, forcar=dados.forcar
        )
    except InsufficientBalanceError as erro:
        # 409 Conflict: the staff panel can show this and offer "force it anyway?"
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(erro),
                "aluno_id": erro.aluno_id,
                "saldo_centavos": erro.saldo_centavos,
                "valor_centavos": erro.valor_centavos,
                "action": "retry the same request with forcar=true to confirm anyway",
            },
        )

    return resultado.aluno


# ---------- Payment requests ----------

@router.get("/pagamentos/pendentes", response_model=list[SolicitacaoPagamentoOut])
def listar_pagamentos_pendentes(db: Session = Depends(get_db)):
    """List parents waiting to be contacted about a payment."""
    stmt = (
        select(SolicitacaoPagamento)
        .where(SolicitacaoPagamento.resolvida.is_(False))
        .order_by(SolicitacaoPagamento.criado_em)
    )
    return db.execute(stmt).scalars().all()


@router.post("/pagamentos/{solicitacao_id}/resolver", response_model=SolicitacaoPagamentoOut)
def resolver_pagamento(solicitacao_id: int, db: Session = Depends(get_db)):
    """Mark a payment request as handled (staff already talked to the parent)."""
    solicitacao = db.get(SolicitacaoPagamento, solicitacao_id)
    if solicitacao is None:
        raise HTTPException(status_code=404, detail="Payment request not found")

    solicitacao.resolvida = True
    db.commit()
    db.refresh(solicitacao)
    return solicitacao
