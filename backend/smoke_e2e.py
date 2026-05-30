"""Integração ponta a ponta: seed → varredura real → consulta rankeada."""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import ListingScore, VehicleListing
from app.seed import init_db
from app.services.scrape import run_active_monitors

init_db()
db = SessionLocal()
try:
    resumo = run_active_monitors(db)
    print("\nRESUMO:", resumo)

    total = db.scalar(select(VehicleListing).where(VehicleListing.ativo.is_(True)).limit(1))
    n_list = len(db.scalars(select(VehicleListing)).all())
    n_score = len(db.scalars(select(ListingScore)).all())
    print(f"listings={n_list} | scores={n_score}\n")

    rows = db.execute(
        select(VehicleListing, ListingScore)
        .join(ListingScore, ListingScore.listing_id == VehicleListing.id)
        .order_by(ListingScore.score.desc().nullslast())
        .limit(8)
    ).all()
    print("TOP por score:")
    for l, s in rows:
        print(f"  desc={ (s.desconto or 0)*100:6.1f}% [{s.origem_score or '-':7}] "
              f"R$ {l.preco!s:>8} ref={s.preco_ref!s:>8} | {l.km!s:>7}km | "
              f"{(l.versao or '')[:40]}")
finally:
    db.close()
