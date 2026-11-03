"""Rotas de login e logout do painel da tia."""
import time
from html import escape

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CHAVE_SESSAO, esta_logado, senha_confere
from app.config import settings

router = APIRouter(tags=["auth"])


def _pagina_login(erro: str = "") -> str:
    aviso = f'<p class="erro">{escape(erro)}</p>' if erro else ""
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Entrar · {escape(settings.cantina_nome)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:16px;
           font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
           background:#fffaf3; color:#2b2118; }}
    form {{ width:100%; max-width:360px; background:#fff; border:1px solid #f0e3d3;
           border-radius:14px; padding:24px; }}
    h1 {{ font-size:1.3rem; margin:0 0 4px; }}
    p.sub {{ color:#6b5b4d; margin:0 0 18px; }}
    label {{ display:block; font-weight:600; margin:12px 0 4px; }}
    input {{ width:100%; padding:10px 12px; border:1px solid #e2d3c0; border-radius:8px; font-size:1rem; }}
    button {{ width:100%; margin-top:18px; padding:11px; border:0; border-radius:999px;
             background:#c2410c; color:#fff; font-weight:700; font-size:1rem; cursor:pointer; }}
    .erro {{ background:#fee2e2; color:#991b1b; padding:8px 12px; border-radius:8px; margin:0 0 8px; }}
  </style>
</head>
<body>
  <form method="post" action="/login">
    <h1>{escape(settings.cantina_nome)}</h1>
    <p class="sub">Painel da cantina</p>
    {aviso}
    <label for="usuario">Usuário</label>
    <input id="usuario" name="usuario" autocomplete="username" required>
    <label for="senha">Senha</label>
    <input id="senha" name="senha" type="password" autocomplete="current-password" required>
    <button type="submit">Entrar</button>
  </form>
</body>
</html>"""


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def tela_login(request: Request):
    if esta_logado(request):
        return RedirectResponse("/painel", status_code=303)
    return HTMLResponse(_pagina_login())


@router.post("/login", include_in_schema=False)
def fazer_login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    if not senha_confere(usuario, senha):
        # Pequena espera para dificultar tentativas em massa de senha.
        time.sleep(1)
        return HTMLResponse(_pagina_login("Usuário ou senha incorretos."), status_code=401)

    request.session.clear()
    request.session[CHAVE_SESSAO] = True
    return RedirectResponse("/painel", status_code=303)


@router.get("/logout", include_in_schema=False)
def sair(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
