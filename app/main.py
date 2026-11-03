"""FastAPI application entrypoint.

Run locally with: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import esta_logado
from app.config import settings
from app.database import criar_tabelas
from app.routers import admin, auth, whatsapp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database tables on startup if they don't exist yet.
    criar_tabelas()
    yield


app = FastAPI(title="Chatbot Cantina", lifespan=lifespan)

# Signed session cookie used by the staff login (expires after 12 hours).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.sessao_cookie_segura,
    same_site="lax",
    max_age=12 * 60 * 60,
)

app.include_router(whatsapp.router)
app.include_router(admin.router)
app.include_router(auth.router)


# Staff admin panel: only reachable after logging in.
@app.get("/painel", include_in_schema=False)
@app.get("/painel/", include_in_schema=False)
@app.get("/painel/admin.html", include_in_schema=False)
def painel(request: Request):
    if not esta_logado(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse("app/static/admin.html")


# Public site: landing page + privacy policy (LGPD), served separately
# from the admin panel (which lives at /painel).
@app.get("/", include_in_schema=False)
def pagina_inicial():
    return FileResponse("app/static/site/index.html")


@app.get("/privacidade", include_in_schema=False)
def politica_privacidade():
    return FileResponse("app/static/site/privacidade.html")



@app.get("/health")
def health_check():
    """Simple endpoint to confirm the API is up."""
    return {"status": "ok"}
