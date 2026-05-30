"""CRUD de monitores."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Monitor
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


@router.get("", response_model=list[MonitorRead])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Monitor).order_by(Monitor.criado_em.desc())).all()


@router.post("", response_model=MonitorRead, status_code=201)
def criar(payload: MonitorCreate, db: Session = Depends(get_db)):
    m = Monitor(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{monitor_id}", response_model=MonitorRead)
def obter(monitor_id: int, db: Session = Depends(get_db)):
    m = db.get(Monitor, monitor_id)
    if not m:
        raise HTTPException(404, "monitor não encontrado")
    return m


@router.patch("/{monitor_id}", response_model=MonitorRead)
def atualizar(monitor_id: int, payload: MonitorUpdate, db: Session = Depends(get_db)):
    m = db.get(Monitor, monitor_id)
    if not m:
        raise HTTPException(404, "monitor não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{monitor_id}", status_code=204)
def remover(monitor_id: int, db: Session = Depends(get_db)):
    m = db.get(Monitor, monitor_id)
    if m:
        db.delete(m)
        db.commit()
