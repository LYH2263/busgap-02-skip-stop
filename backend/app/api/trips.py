import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, Trip

router = APIRouter(prefix="/trips", tags=["trips"])


def _serialize(r: Trip) -> dict:
    try:
        skipped = json.loads(r.skipped_stops or "[]")
    except json.JSONDecodeError:
        skipped = []
    return {"id": r.id, "line_id": r.line_id, "trip_no": r.trip_no,
            "planned_depart": r.planned_depart.isoformat(), "vehicle_no": r.vehicle_no,
            "skipped_stops": skipped}


@router.get("")
def list_trips(line_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Trip).order_by(Trip.planned_depart)
    if line_id is not None:
        q = q.where(Trip.line_id == line_id)
    return [_serialize(r) for r in db.scalars(q).all()]


class SkipUpdate(BaseModel):
    skipped_stops: list[str]


@router.put("/{trip_id}")
def update_trip(trip_id: int, body: SkipUpdate, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "班次不存在")
    new_skipped = set(body.skipped_stops)

    # 线路上全部站点（站序取其他班次已有记录）
    stop_rows = db.execute(
        select(Arrival.stop_name, Arrival.stop_seq)
        .join(Trip, Arrival.trip_id == Trip.id)
        .where(Trip.line_id == trip.line_id)
        .group_by(Arrival.stop_name, Arrival.stop_seq)
        .order_by(Arrival.stop_seq)
    ).all()
    stop_seq_map = {name: seq for name, seq in stop_rows}

    try:
        old_skipped = set(json.loads(trip.skipped_stops or "[]"))
    except json.JSONDecodeError:
        old_skipped = set()

    # 新越站：删除该站到站，时间轴/报告/到站页都不再出现这班
    for stop in new_skipped - old_skipped:
        for a in db.scalars(select(Arrival).where(Arrival.trip_id == trip.id, Arrival.stop_name == stop)).all():
            db.delete(a)

    # 取消越站：补登记到站，按计划发班后每站 6 分钟估算，班次重新参与该站
    for stop in old_skipped - new_skipped:
        exists = db.scalar(select(Arrival).where(Arrival.trip_id == trip.id, Arrival.stop_name == stop))
        if not exists and stop in stop_seq_map:
            db.add(Arrival(trip_id=trip.id, stop_name=stop, stop_seq=stop_seq_map[stop],
                           actual_arrive=trip.planned_depart + timedelta(minutes=stop_seq_map[stop] * 6)))

    trip.skipped_stops = json.dumps(sorted(new_skipped), ensure_ascii=False)
    db.commit()
    return _serialize(trip)
