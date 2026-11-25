"""Notificações por e-mail com anti-spam (§4.5).

Anti-spam em duas camadas:
  - MonitorMatch é único por (monitor, listing) → cada anúncio casa uma vez.
  - Notification registra o envio → nunca reenvia o mesmo anúncio ao mesmo monitor.
"""
from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ListingScore,
    Monitor,
    MonitorMatch,
    Notification,
    VehicleListing,
)

log = logging.getLogger(__name__)


def registrar_match(
    db: Session, monitor: Monitor, listing: VehicleListing, desconto: float, posicao: int
) -> bool:
    """Cria o MonitorMatch se inédito. Retorna True se for novo."""
    ja = db.scalar(
        select(MonitorMatch).where(
            MonitorMatch.monitor_id == monitor.id,
            MonitorMatch.listing_id == listing.id,
        )
    )
    if ja:
        ja.posicao_ranking = posicao
        return False
    db.add(MonitorMatch(monitor_id=monitor.id, listing_id=listing.id,
                        desconto=desconto, posicao_ranking=posicao))
    db.flush()
    return True


def _ja_notificado(db: Session, monitor_id: int, listing_id: int) -> bool:
    return db.scalar(
        select(exists().where(
            Notification.monitor_id == monitor_id,
            Notification.listing_id == listing_id,
            Notification.status == "enviado",
        ))
    )


def _brl(v) -> str:
    return "—" if v is None else "R$ " + f"{int(v):,}".replace(",", ".")


def _html_resumo(monitor: Monitor, itens: list) -> str:
    """E-mail HTML: um card por carro (foto, preço, % abaixo do mercado, link)."""
    linhas = []
    for listing, score in itens[:15]:
        desc = (score.desconto or 0) * 100
        foto = (f'<img src="{listing.foto_url}" width="120" style="border-radius:6px;'
                f'display:block" alt="">') if listing.foto_url else ""
        local = " · ".join(filter(None, [listing.cidade, listing.uf]))
        km = f"{listing.km:,} km".replace(",", ".") if listing.km else "km n/d"
        linhas.append(f"""
        <tr><td style="padding:10px;border-bottom:1px solid #eee;width:130px">{foto}</td>
        <td style="padding:10px;border-bottom:1px solid #eee;font-family:Arial,sans-serif">
          <div style="font-weight:bold;color:#1e293b">{listing.versao or listing.modelo or 'Veículo'}</div>
          <div style="color:#dc2626;font-size:18px;font-weight:bold">{_brl(listing.preco)}</div>
          <div style="color:#64748b;font-size:13px">{listing.ano_modelo or '—'} · {km} · {local}</div>
          <div style="color:#059669;font-size:13px;font-weight:bold">{desc:.0f}% abaixo do mercado
            <span style="color:#94a3b8;font-weight:normal">(justo {_brl(score.preco_ref)})</span></div>
          <a href="{listing.url}" style="color:#0284c7;font-size:13px">Ver anúncio →</a>
        </td></tr>""")
    extra = (f'<p style="color:#64748b">+ {len(itens) - 15} outros no app.</p>'
             if len(itens) > 15 else "")
    return f"""<div style="max-width:600px;margin:auto">
      <h2 style="font-family:Arial,sans-serif;color:#0f172a">🚗 {len(itens)} oportunidade(s) — {monitor.nome}</h2>
      <table style="width:100%;border-collapse:collapse">{''.join(linhas)}</table>{extra}
      <p style="font-family:Arial,sans-serif;color:#94a3b8;font-size:12px">
        CarPrice · você recebe isto porque o monitor "{monitor.nome}" está ativo.</p></div>"""


def enviar_resumo(db: Session, monitor: Monitor, itens: list) -> bool:
    """UM e-mail por monitor com todos os carros NOVOS da varredura (em vez de um
    e-mail por carro). Registra uma Notification por anúncio (anti-reenvio)."""
    itens = [(l, s) for (l, s) in itens if not _ja_notificado(db, monitor.id, l.id)]
    if not itens:
        return False
    destino = (monitor.criterios_json or {}).get("email_destino") or (
        monitor.user.email if monitor.user else None
    )

    def registra(status: str, erro: str | None = None) -> None:
        agora = datetime.now(timezone.utc) if status == "enviado" else None
        for listing, _s in itens:
            db.add(Notification(monitor_id=monitor.id, listing_id=listing.id, canal="email",
                                status=status, erro=erro, enviado_em=agora))

    if not settings.smtp_configured or not destino:
        registra("ignorado", "SMTP não configurado ou destino ausente")
        log.info("[email simulado] %d carro(s) → %s", len(itens), destino)
        return False

    try:
        msg = MIMEText(_html_resumo(monitor, itens), "html", _charset="utf-8")
        melhor = max((s.desconto or 0) for _l, s in itens) * 100
        msg["Subject"] = (f"[CarPrice] {len(itens)} oportunidade(s) em “{monitor.nome}” "
                          f"— até {melhor:.0f}% abaixo do mercado")
        msg["From"] = settings.smtp_from
        msg["To"] = destino
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as srv:
            if settings.smtp_use_tls:
                srv.starttls()
            if settings.smtp_user:
                srv.login(settings.smtp_user, settings.smtp_password)
            srv.send_message(msg)
        registra("enviado")
        return True
    except Exception as e:  # noqa: BLE001
        registra("falha", str(e))
        log.warning("falha ao enviar e-mail: %s", e)
        return False
