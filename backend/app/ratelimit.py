"""Rate limit simples em memória (janela deslizante por IP).

Protege o que é caro ou sensível: login/cadastro (força bruta) e a busca ao vivo
(raspagem de 6 portais por requisição). O serviço roda com 1 instância, então um
dicionário em memória basta.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

_hits: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def ip_do_cliente(request: Request) -> str:
    """IP real atrás do proxy do Render (1º item do X-Forwarded-For)."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def limite(nome: str, maximo: int, janela_s: int):
    """Dependência FastAPI: no máximo `maximo` chamadas por IP a cada `janela_s`."""

    def _dep(request: Request) -> None:
        chave = f"{nome}:{ip_do_cliente(request)}"
        agora = time.monotonic()
        with _lock:
            fila = _hits[chave]
            while fila and agora - fila[0] > janela_s:
                fila.popleft()
            if len(fila) >= maximo:
                espera = int(janela_s - (agora - fila[0])) + 1
                raise HTTPException(
                    429, f"muitas tentativas — aguarde {espera}s e tente de novo")
            fila.append(agora)

    return _dep


def zerar() -> None:
    """Limpa os contadores (usado nos testes)."""
    with _lock:
        _hits.clear()
