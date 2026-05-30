"""Registro de conectores. Adicionar um portal novo = adicionar uma linha aqui."""
from __future__ import annotations

from app.collectors.base import PortalConnector
from app.collectors.carrosp import CarroSPConnector
from app.collectors.comprecar import ComprecarConnector
from app.collectors.icarros import ICarrosConnector
from app.collectors.localiza import LocalizaConnector
from app.collectors.mobiauto import MobiautoConnector
from app.collectors.napista import NapistaConnector

_CONNECTORS: list[type[PortalConnector]] = [
    NapistaConnector,
    CarroSPConnector,
    ComprecarConnector,
    ICarrosConnector,
    LocalizaConnector,
    MobiautoConnector,
]

REGISTRY: dict[str, PortalConnector] = {c.slug: c() for c in _CONNECTORS}


def get_connector(slug: str) -> PortalConnector | None:
    return REGISTRY.get(slug)


def all_connectors() -> list[PortalConnector]:
    return list(REGISTRY.values())
