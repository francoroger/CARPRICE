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


def _corpo(listing: VehicleListing, score: ListingScore, posicao: int) -> str:
    desc_pct = f"{(score.desconto or 0) * 100:.1f}%"
    return (
        f"Oportunidade encontrada (#{posicao} no ranking)\n\n"
        f"{listing.versao or listing.titulo or 'Veículo'}\n"
        f"Ano: {listing.ano_modelo or '-'}  |  Km: {listing.km or '-'}\n"
        f"Preço: R$ {listing.preco:,}\n".replace(",", ".") +
        f"Desconto vs. idênticos: {desc_pct}  (origem: {score.origem_score})\n"
        f"Preço de referência: R$ {score.preco_ref or '-'}\n"
        f"Local: {listing.cidade or '-'}/{listing.uf or '-'}\n\n"
        f"Link: {listing.url}\n"
    )


def enviar_email(
    db: Session, monitor: Monitor, listing: VehicleListing, score: ListingScore, posicao: int
) -> bool:
    """Envia e-mail do anúncio. Retorna True se enviou. Registra em notifications."""
    if _ja_notificado(db, monitor.id, listing.id):
        return False

    destino = (monitor.criterios_json or {}).get("email_destino") or (
        monitor.user.email if monitor.user else None
    )
    notif = Notification(monitor_id=monitor.id, listing_id=listing.id, canal="email")

    if not settings.smtp_configured or not destino:
        notif.status = "ignorado"
        notif.erro = "SMTP não configurado ou destino ausente"
        db.add(notif)
        log.info("[email simulado] %s → %s", listing.url, destino)
        return False

    try:
        msg = MIMEText(_corpo(listing, score, posicao), _charset="utf-8")
        msg["Subject"] = f"[CarPrice] {listing.versao or listing.titulo} — {(score.desconto or 0)*100:.0f}% abaixo"
        msg["From"] = settings.smtp_from
        msg["To"] = destino

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as srv:
            if settings.smtp_use_tls:
                srv.starttls()
            if settings.smtp_user:
                srv.login(settings.smtp_user, settings.smtp_password)
            srv.send_message(msg)

        notif.status = "enviado"
        notif.enviado_em = datetime.now(timezone.utc)
        db.add(notif)
        return True
    except Exception as e:
        notif.status = "falha"
        notif.erro = str(e)
        db.add(notif)
        log.warning("falha ao enviar e-mail: %s", e)
        return False
