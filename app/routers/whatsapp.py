"""WhatsApp router: the webhook that receives messages and drives the
conversation state machine.

Conversation states (per phone number, stored in `EstadoConversa.etapa`):
 - "cadastro_nome": waiting for the parent's name (first contact ever)
 - "cadastro_qtd_filhos": waiting for how many children to register
 - "cadastro_dados_filho": collecting each child's name/grade/shift, one at a time
 - "menu": normal menu (view the day's menu, view balance)
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Aluno, EstadoConversa, Produto, Responsavel

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """Handshake Meta requires to confirm this endpoint is really ours."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/webhook")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    mensagem = _extract_message(payload)

    if mensagem is None:
        # Not a text message we handle (e.g. a delivery/read status update).
        return {"status": "ignored"}

    numero, texto = mensagem
    resposta = process_message(db, numero, texto)
    send_message(numero, resposta)

    return {"status": "ok"}


def _extract_message(payload: dict) -> tuple[str, str] | None:
    """Pull (phone_number, text) out of Meta's webhook payload, if present."""
    try:
        entrada = payload["entry"][0]["changes"][0]["value"]
        mensagens = entrada.get("messages")
        if not mensagens:
            return None
        msg = mensagens[0]
        if msg.get("type") != "text":
            return None
        return msg["from"], msg["text"]["body"].strip()
    except (KeyError, IndexError):
        return None


def send_message(numero: str, texto: str) -> None:
    """Send a WhatsApp message back to the user.

    Stub for now — this print will be replaced by the real Meta Graph API
    call once we have an access token and phone number id configured.
    """
    print(f"[WHATSAPP -> {numero}] {texto}")


def process_message(db: Session, numero: str, texto: str) -> str:
    estado = db.get(EstadoConversa, numero)

    if estado is None:
        # First contact ever from this number: start registration.
        estado = EstadoConversa(whatsapp_number=numero, etapa="cadastro_nome", contexto_json="{}")
        db.add(estado)
        db.commit()
        return (
            f"Olá! Bem-vindo(a) à {settings.cantina_nome}. "
            "Pra começar, qual é o seu nome (responsável)?"
        )

    if estado.etapa == "cadastro_nome":
        contexto = {"responsavel_nome": texto}
        estado.etapa = "cadastro_qtd_filhos"
        estado.contexto_json = json.dumps(contexto)
        db.commit()
        return "Quantos filhos você tem para cadastrar na cantina?"

    if estado.etapa == "cadastro_qtd_filhos":
        try:
            quantidade = int(texto)
            assert quantidade > 0
        except (ValueError, AssertionError):
            return "Por favor, responda só com um número (ex: 1, 2, 3...)."

        contexto = json.loads(estado.contexto_json)
        contexto["quantidade_filhos"] = quantidade
        contexto["filhos_cadastrados"] = []
        estado.etapa = "cadastro_dados_filho"
        estado.contexto_json = json.dumps(contexto)
        db.commit()
        return _ask_next_child(contexto)

    if estado.etapa == "cadastro_dados_filho":
        return _continue_child_registration(db, estado, texto)

    if estado.etapa == "menu":
        return _handle_menu_option(db, numero, texto)

    # Fallback: should not normally happen, but keeps the flow from getting stuck.
    estado.etapa = "menu"
    db.commit()
    return _main_menu()


def _ask_next_child(contexto: dict) -> str:
    indice = len(contexto["filhos_cadastrados"]) + 1
    return (
        f"Dados do filho(a) {indice} de {contexto['quantidade_filhos']}:\n"
        "Envie no formato: nome completo, série, turno (manha/tarde)."
    )


def _continue_child_registration(db: Session, estado: EstadoConversa, texto: str) -> str:
    contexto = json.loads(estado.contexto_json)

    partes = [p.strip() for p in texto.split(",")]
    if len(partes) != 3:
        return "Formato inválido. Envie assim: nome completo, série, turno (manha/tarde)."

    nome, serie, turno = partes
    contexto["filhos_cadastrados"].append({"nome": nome, "serie": serie, "turno": turno})

    if len(contexto["filhos_cadastrados"]) < contexto["quantidade_filhos"]:
        estado.contexto_json = json.dumps(contexto)
        db.commit()
        return _ask_next_child(contexto)

    # Got everyone: persist the parent + children, then move to the main menu.
    responsavel = Responsavel(
        nome=contexto["responsavel_nome"], whatsapp_number=estado.whatsapp_number
    )
    db.add(responsavel)
    db.flush()  # need responsavel.id before creating the children

    for filho in contexto["filhos_cadastrados"]:
        db.add(
            Aluno(
                responsavel_id=responsavel.id,
                nome=filho["nome"],
                serie=filho["serie"],
                turno=filho["turno"],
            )
        )

    estado.etapa = "menu"
    estado.contexto_json = "{}"
    db.commit()

    return "Cadastro concluído!\n\n" + _main_menu()


def _main_menu() -> str:
    return "O que você gostaria de fazer?\n1 - Ver cardápio\n2 - Como fazer pagamento\n3 - Ver saldo"


def _handle_menu_option(db: Session, numero: str, texto: str) -> str:
    if texto == "1":
        produtos = db.execute(
            select(Produto).where(Produto.disponivel.is_(True))
        ).scalars().all()
        if not produtos:
            return "No momento não há itens disponíveis no cardápio."
        linhas = [f"- {p.nome}: R$ {p.preco_centavos / 100:.2f}" for p in produtos]
        return "Cardápio de hoje:\n" + "\n".join(linhas)

    if texto == "2":
        # MVP: credit is still entered manually by the staff (see ADR about
        # deferring automatic Pix payments). This just explains how it works
        # today, it doesn't process any payment.
        return (
            "Para colocar crédito, combine o pagamento diretamente com a tia "
            "da cantina. Assim que ela confirmar, o saldo é atualizado."
        )

    if texto == "3":
        responsavel = db.execute(
            select(Responsavel).where(Responsavel.whatsapp_number == numero)
        ).scalar_one_or_none()
        if responsavel is None or not responsavel.alunos:
            return "Não encontrei nenhum filho cadastrado nesse número."
        linhas = [
            f"- {aluno.nome}: R$ {aluno.saldo_centavos / 100:.2f}"
            for aluno in responsavel.alunos
        ]
        return "Saldo atual:\n" + "\n".join(linhas)

    return "Não entendi. " + _main_menu()
