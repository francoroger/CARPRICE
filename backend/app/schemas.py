"""Schemas Pydantic (entrada/saída da API)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MonitorBase(BaseModel):
    nome: str
    criterios_json: dict = {}
    frequencia_min: int = 60
    threshold_desconto: float = 0.08
    canais_notif: list[str] = ["email"]
    status: str = "ativo"


class MonitorCreate(MonitorBase):
    pass


class MonitorUpdate(BaseModel):
    nome: str | None = None
    criterios_json: dict | None = None
    frequencia_min: int | None = None
    threshold_desconto: float | None = None
    canais_notif: list[str] | None = None
    status: str | None = None


class MonitorRead(MonitorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criado_em: datetime
    ultima_exec_em: datetime | None = None


class PortalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    slug: str
    min_tier: int
    rate_limit_s: float
    ativo: bool


class ListingRead(BaseModel):
    id: int
    portal_slug: str | None = None
    url: str
    titulo: str | None = None
    marca: str | None = None
    modelo: str | None = None
    versao: str | None = None
    ano_modelo: int | None = None
    preco: int | None = None
    km: int | None = None
    faixa_km: str | None = None
    cidade: str | None = None
    uf: str | None = None
    foto_url: str | None = None
    # score
    preco_ref: int | None = None
    desconto: float | None = None
    origem_score: str | None = None
    score: float | None = None


class ScrapeLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    portal_id: int | None = None
    monitor_id: int | None = None
    tier_usado: int | None = None
    status: str
    qtd_resultados: int
    erro: str | None = None
    duracao_ms: int | None = None
    executado_em: datetime


class SearchRequest(BaseModel):
    """Critérios da busca ao vivo (modelados nos filtros do CarroSP)."""
    marca: str | None = None
    modelo: str | None = None
    versao: str | None = None
    uf: str | None = None
    cidade: str | None = None
    raio_km: int | None = None
    ano_min: int | None = None
    ano_max: int | None = None
    preco_min: int | None = None
    preco_max: int | None = None
    km_min: int | None = None
    km_max: int | None = None
    cambio: str | None = None
    combustivel: str | None = None
    cor: str | None = None
    condicao: str | None = None  # "0km" | "usado"
    ordenar: str = "preco_asc"   # preco_asc | preco_desc | desconto
    forcar: bool = False         # True = ignora cache e coleta ao vivo de novo


class PortalStatus(BaseModel):
    portal: str
    status: str
    qtd: int
    erro: str | None = None


class SearchResponse(BaseModel):
    total: int
    portais: list[PortalStatus]
    resultados: list[ListingRead]


class SettingUpdate(BaseModel):
    valor_json: dict | list | float | int | str


class ScoreParamsRead(BaseModel):
    min_grupo: int
    alpha_km: float
    cap_km: float
    threshold_desconto: float
    faixas_km: list[int]
