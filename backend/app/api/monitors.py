"""CRUD de monitores — escopados por usuário quando logado (convidado vê os sem dono)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_opcional
from app.models import Monitor, User
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


def _dono_ok(m: Monitor, user: User | None) -> bool:
    """Logado: só os seus. Convidado: só os sem dono (user_id nulo)."""
    return m.user_id == (user.id if user else None)


@router.get("", response_model=list[MonitorRead])
def listar(user: User | None = Depends(usuario_opcional), db: Session = Depends(get_db)):
    q = (select(Monitor)
         .where(Monitor.user_id == (user.id if user else None))
         .order_by(Monitor.criado_em.desc()))
    return db.scalars(q).all()


@router.post("", response_model=MonitorRead, status_code=201)
def criar(payload: MonitorCreate, user: User | None = Depends(usuario_opcional),
          db: Session = Depends(get_db)):
    m = Monitor(**payload.model_dump(), user_id=user.id if user else None)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{monitor_id}", response_model=MonitorRead)
def obter(monitor_id: int, user: User | None = Depends(usuario_opcional),
          db: Session = Depends(get_db)):
    m = db.get(Monitor, monitor_id)
    if not m or not _dono_ok(m, user):
        raise HTTPException(404, "monitor não encontrado")
    return m


@router.patch("/{monitor_id}", response_model=MonitorRead)
def atualizar(monitor_id: int, payload: MonitorUpdate,
              user: User | None = Depends(usuario_opcional), db: Session = Depends(get_db)):
    m = db.get(Monitor, monitor_id)
    if not m or not _dono_ok(m, user):
        raise HTTPException(404, "monitor não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{monitor_id}", status_code=204)
def remover(monitor_id: int, user: User | None = Depends(usuario_opcional),
            db: Session = Depends(get_db)):
    m = db.get(Monitor, monitor_id)
    if m and _dono_ok(m, user):
        db.delete(m)
        db.commit()
