from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import Arrival, Line, Trip
import json

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Line)) or 0) > 0:
        return
    base = datetime(2026, 9, 17, 7, 0, 0)
    line = Line(code="B12", name="城东环线", planned_headway_min=8.0, bunch_threshold=3.0, large_threshold=15.0)
    db.add(line); db.flush()
    # (班次号, 车牌号, 发班偏移分钟, 越站站名列表)
    specs = [
        ("T01", "粤A1001", 0, []),
        ("T02", "粤A1002", 2, ["市民中心"]),
        ("T03", "粤A1003", 18, []),
        ("T04", "粤A1004", 26, []),
    ]
    stops = ["起点站", "市民中心", "火车站", "终点站"]
    for trip_no, vehicle, offset, skipped in specs:
        trip = Trip(line_id=line.id, trip_no=trip_no, planned_depart=base + timedelta(minutes=offset),
                    vehicle_no=vehicle, skipped_stops=json.dumps(skipped, ensure_ascii=False))
        db.add(trip); db.flush()
        for seq, stop in enumerate(stops):
            if stop in skipped:
                continue  # 越站不停：不登记该站到站
            arrive = base + timedelta(minutes=offset + seq * 6)
            if stop == "火车站" and trip_no == "T03":
                arrive = base + timedelta(minutes=30)
            db.add(Arrival(trip_id=trip.id, stop_name=stop, stop_seq=seq, actual_arrive=arrive))
    db.commit()
