"""Configuração via variáveis de ambiente (pydantic-settings).

Toda credencial e parâmetro de infra vive aqui — nada hardcoded nos módulos.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco
    database_url: str = "sqlite:///./carprice.db"

    # Auth (JWT). Em produção, definir JWT_SECRET no ambiente do Render.
    jwt_secret: str = "dev-secret-trocar-em-producao"
    jwt_expira_dias: int = 30

    # Agendador
    scrape_default_interval_min: int = 60
    scheduler_enabled: bool = True

    # E-mail / SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alertas@carprice.local"
    smtp_use_tls: bool = True

    # Coleta HTTP
    http_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    http_timeout_s: int = 30

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
