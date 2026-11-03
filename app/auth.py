"""Autenticação do painel da tia (um único usuário administrador).

A senha nunca fica em texto puro: o .env guarda só o hash bcrypt dela.
Depois do login, o navegador recebe um cookie de sessão assinado com a
SECRET_KEY (ninguém consegue falsificar sem conhecer a chave).
"""
import hmac

import bcrypt
from fastapi import HTTPException, Request, status

from app.config import settings

CHAVE_SESSAO = "admin_logado"


def senha_confere(usuario: str, senha: str) -> bool:
    """Confere usuário e senha contra os valores do .env."""
    if not settings.admin_senha_hash:
        # Sem hash configurado, ninguém entra (evita painel aberto por engano).
        return False

    # compare_digest evita ataques que medem o tempo da comparação.
    usuario_ok = hmac.compare_digest(usuario.encode(), settings.admin_usuario.encode())
    try:
        senha_ok = bcrypt.checkpw(senha.encode(), settings.admin_senha_hash.encode())
    except ValueError:
        # Hash mal formatado no .env.
        return False
    return usuario_ok and senha_ok


def esta_logado(request: Request) -> bool:
    return request.session.get(CHAVE_SESSAO) is True


def exigir_login(request: Request) -> None:
    """Dependência do FastAPI: bloqueia a rota se não houver login."""
    if not esta_logado(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login necessário")
