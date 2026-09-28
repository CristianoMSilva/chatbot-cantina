"""Configuração da aplicação, lida a partir de variáveis de ambiente (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"

    whatsapp_verify_token: str = "dev-token"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    cantina_nome: str = "Cantina Tia Eleusa"
    escola_nome: str = "Colégio Athena"


settings = Settings()
