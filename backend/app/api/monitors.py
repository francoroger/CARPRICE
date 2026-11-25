"""CRUD de monitores — sempre de um usuário logado.

Monitor anônimo não existe mais: qualquer visitante criava monitores que rodavam
na varredura de todos (custo/abuso) e eram visíveis/apagáveis por qualquer outro.
Convidado lista vazio e é convidado a entrar.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual, usuario_opcional
from app.models import Monitor, Notification, ScrapeLog, User
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


def _do_usuario(db: Session, monitor_id: int, user: User) -> Monitor:
    m = db.get(Monitor, monitor_id)
    if not m or m.user_id != user.id:
        raise HTTPException(404, "monitor não encontrado")
    return m


@router.get("", response_model=list[MonitorRead])
def listar(user: User | None = Depends(usuario_opcional), db: Session = Depends(get_db)):
    if not user:
        return []
    return db.scalars(
        select(Monitor).where(Monitor.user_id == user.id)
        .order_by(Monitor.criado_em.desc())
    ).all()


@router.post("", response_model=MonitorRead, status_code=201)
def criar(payload: MonitorCreate, user: User = Depends(usuario_atual),
          db: Session = Depends(get_db)):
    m = Monitor(**payload.model_dump(), user_id=user.id)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{monitor_id}", response_model=MonitorRead)
def obter(monitor_id: int, user: User = Depends(usuario_atual),
          db: Session = Depends(get_db)):
    return _do_usuario(db, monitor_id, user)


@router.patch("/{monitor_id}", response_model=MonitorRead)
def atualizar(monitor_id: int, payload: MonitorUpdate,
              user: User = Depends(usuario_atual), db: Session = Depends(get_db)):
    m = _do_usuario(db, monitor_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{monitor_id}", status_code=204)
def remover(monitor_id: int, user: User = Depends(usuario_atual),
            db: Session = Depends(get_db)):
    m = _do_usuario(db, monitor_id, user)
    # FKs sem cascade: limpa as dependências antes (senão o Postgres recusa o DELETE)
    db.execute(delete(Notification).where(Notification.monitor_id == m.id))
    db.execute(update(ScrapeLog).where(ScrapeLog.monitor_id == m.id).values(monitor_id=None))
    db.delete(m)
    db.commit()
