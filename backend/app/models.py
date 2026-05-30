"""Modelo de dados (seção 5 do PROJETO_v3).

Decisão-chave: `VehicleListing` é o MERCADO GLOBAL compartilhado entre todos os
monitores — é o que dá volume estatístico à engine de score. `MonitorMatch` é a
relação monitor↔anúncio, usada só para decidir o que notificar.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AccessTier(enum.IntEnum):
    """Nível de acesso do motor de coleta (ver §2 do projeto)."""

    HTTP = 1        # httpx + headers de navegador (CarroSP, iCarros, Napista, ...)
    SESSION = 2     # httpx + aquecimento de sessão (APIs JSON de SPAs)
    BROWSER = 3     # Playwright + stealth
    PROXY = 4       # proxy residencial rotativo
    UNBLOCKER = 5   # API unblocker paga (PerimeterX: Webmotors/OLX)


class MonitorStatus(str, enum.Enum):
    ATIVO = "ativo"
    PAUSADO = "pausado"


class ScoreOrigin(str, enum.Enum):
    MERCADO = "MERCADO"
    FIPE = "FIPE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    senha_hash: Mapped[str] = mapped_column(String(255), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    monitors: Mapped[list[Monitor]] = relationship(back_populates="user")


class Portal(Base):
    __tablename__ = "portals"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    min_tier: Mapped[int] = mapped_column(Integer, default=AccessTier.HTTP)
    rate_limit_s: Mapped[float] = mapped_column(Float, default=2.0)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    listings: Mapped[list[VehicleListing]] = relationship(back_populates="portal")


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    nome: Mapped[str] = mapped_column(String(160))
    # filtros da busca salva: marca, modelo, versao, ano_*, preco_*, km_max, uf, cidade...
    criterios_json: Mapped[dict] = mapped_column(JSON, default=dict)
    frequencia_min: Mapped[int] = mapped_column(Integer, default=60)
    threshold_desconto: Mapped[float] = mapped_column(Float, default=0.08)
    canais_notif: Mapped[list] = mapped_column(JSON, default=lambda: ["email"])
    status: Mapped[str] = mapped_column(String(20), default=MonitorStatus.ATIVO.value)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ultima_exec_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User | None] = relationship(back_populates="monitors")
    matches: Mapped[list[MonitorMatch]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )


class VehicleListing(Base):
    """MERCADO GLOBAL — todos os anúncios coletados, de todos os portais."""

    __tablename__ = "vehicle_listings"
    __table_args__ = (UniqueConstraint("hash_dedup", name="uq_listing_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    portal_id: Mapped[int] = mapped_column(ForeignKey("portals.id"), index=True)
    url: Mapped[str] = mapped_column(Text)

    marca: Mapped[str | None] = mapped_column(String(60), index=True)
    modelo: Mapped[str | None] = mapped_column(String(120), index=True)
    versao: Mapped[str | None] = mapped_column(String(200))
    ano_fab: Mapped[int | None] = mapped_column(Integer)
    ano_modelo: Mapped[int | None] = mapped_column(Integer, index=True)

    preco: Mapped[int | None] = mapped_column(Integer, index=True)
    km: Mapped[int | None] = mapped_column(Integer)
    faixa_km: Mapped[str | None] = mapped_column(String(20))
    cambio: Mapped[str | None] = mapped_column(String(30))
    combustivel: Mapped[str | None] = mapped_column(String(30))
    cidade: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    foto_url: Mapped[str | None] = mapped_column(Text)

    grupo_chave: Mapped[str | None] = mapped_column(String(300), index=True)
    hash_dedup: Mapped[str] = mapped_column(String(64), index=True)

    fipe_codigo: Mapped[str | None] = mapped_column(String(20))
    fipe_valor: Mapped[int | None] = mapped_column(Integer)

    primeiro_visto_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    ultimo_visto_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    portal: Mapped[Portal] = relationship(back_populates="listings")
    scores: Mapped[list[ListingScore]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class ListingScore(Base):
    """Score recalculado a cada varredura para cada anúncio."""

    __tablename__ = "listing_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_listings.id"), index=True
    )
    preco_ref: Mapped[int | None] = mapped_column(Integer)
    desconto: Mapped[float | None] = mapped_column(Float, index=True)
    origem_score: Mapped[str | None] = mapped_column(String(10))
    score: Mapped[float | None] = mapped_column(Float, index=True)
    calculado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    listing: Mapped[VehicleListing] = relationship(back_populates="scores")


class MonitorMatch(Base):
    """Anúncio que casa com um monitor — base da notificação."""

    __tablename__ = "monitor_matches"
    __table_args__ = (
        UniqueConstraint("monitor_id", "listing_id", name="uq_match_monitor_listing"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"), index=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_listings.id"), index=True
    )
    desconto: Mapped[float | None] = mapped_column(Float)
    posicao_ranking: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    monitor: Mapped[Monitor] = relationship(back_populates="matches")


class FipeCache(Base):
    __tablename__ = "fipe_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo_fipe: Mapped[str | None] = mapped_column(String(20), index=True)
    marca: Mapped[str | None] = mapped_column(String(60))
    modelo: Mapped[str | None] = mapped_column(String(120))
    ano: Mapped[int] = mapped_column(Integer)
    valor: Mapped[int | None] = mapped_column(Integer)
    ref_mes: Mapped[str | None] = mapped_column(String(20))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("vehicle_listings.id"))
    canal: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    erro: Mapped[str | None] = mapped_column(Text)
    enviado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Setting(Base):
    """Parâmetros globais (engine de score, etc.) — chave/valor JSON."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    valor_json: Mapped[dict | list | float | int | str] = mapped_column(JSON)


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    portal_id: Mapped[int | None] = mapped_column(ForeignKey("portals.id"), index=True)
    monitor_id: Mapped[int | None] = mapped_column(ForeignKey("monitors.id"))
    tier_usado: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    qtd_resultados: Mapped[int] = mapped_column(Integer, default=0)
    erro: Mapped[str | None] = mapped_column(Text)
    duracao_ms: Mapped[int | None] = mapped_column(Integer)
    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
