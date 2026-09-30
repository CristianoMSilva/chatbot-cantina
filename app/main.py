"""FastAPI application entrypoint.

Run locally with: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import criar_tabelas
from app.routers import admin, whatsapp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database tables on startup if they don't exist yet.
    criar_tabelas()
    yield


app = FastAPI(title="Chatbot Cantina", lifespan=lifespan)

app.include_router(whatsapp.router)
app.include_router(admin.router)

# Staff admin panel, served as static files at /painel/admin.html
app.mount("/painel", StaticFiles(directory="app/static", html=True), name="painel")


@app.get("/health")
def health_check():
    """Simple endpoint to confirm the API is up."""
    return {"status": "ok"}
