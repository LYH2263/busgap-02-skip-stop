from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.models import Arrival, SkipStop, Trip
router = APIRouter(prefix="/trips", tags=["trips"])

class SkipStopsIn(BaseModel):
    stop_names: list[str] = []

def _trip_payload(t: Trip, skip_map: dict[int, list[str]], stop_map: dict[int, list[str]]) -> dict:
    return {"id": t.id, "line_id": t.line_id, "trip_no": t.trip_no,
            "planned_depart": t.planned_depart.isoformat(), "vehicle_no": t.vehicle_no,
            "stops": stop_map.get(t.id, []), "skip_stops": skip_map.get(t.id, [])}

@router.get("")
def list_trips(line_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Trip).options(joinedload(Trip.arrivals)).order_by(Trip.planned_depart)
    if line_id is not None: q = q.where(Trip.line_id == line_id)
    trips = db.scalars(q).unique().all()
    skip_rows = db.scalars(select(SkipStop).where(SkipStop.trip_id.in_([t.id for t in trips]))).all() if trips else []
    skip_map: dict[int, list[str]] = {}
    for s in skip_rows:
        skip_map.setdefault(s.trip_id, []).append(s.stop_name)
    stop_map: dict[int, list[str]] = {}
    for t in trips:
        stop_map[t.id] = [a.stop_name for a in sorted(t.arrivals, key=lambda a: a.stop_seq)]
        # 仅保留该班次实际经过的站名，过滤掉无效登记
        valid = set(stop_map[t.id])
        skip_map[t.id] = [s for s in skip_map.get(t.id, []) if s in valid]
    return [_trip_payload(t, skip_map, stop_map) for t in trips]

@router.put("/{trip_id}/skip-stops", status_code=200)
def set_skip_stops(trip_id: int, body: SkipStopsIn, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip: raise HTTPException(404, "班次不存在")
    valid = set(db.scalars(select(Arrival.stop_name).where(Arrival.trip_id == trip_id).distinct()).all())
    wanted = [s for s in dict.fromkeys(body.stop_names) if s in valid]
    db.query(SkipStop).filter(SkipStop.trip_id == trip_id).delete(synchronize_session=False)
    db.add_all([SkipStop(trip_id=trip_id, stop_name=s) for s in wanted])
    db.commit()
    return {"id": trip_id, "skip_stops": wanted}
