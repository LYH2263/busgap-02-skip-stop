from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import Arrival, Line, SkipStop, Trip

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Line)) or 0) > 0:
        return
    base = datetime(2026, 9, 17, 7, 0, 0)
    line = Line(code="B12", name="城东环线", planned_headway_min=8.0, bunch_threshold=3.0, large_threshold=15.0)
    db.add(line); db.flush()
    specs = [("T01", "粤A1001", 0), ("T02", "粤A1002", 2), ("T03", "粤A1003", 18), ("T04", "粤A1004", 26)]
    stops = ["起点站", "市民中心", "火车站", "终点站"]
    # 登记越站的班次：该站不到站停靠（仍保留到站记录用于原始留痕，检测/时间轴会剔除）
    skip_specs = {("T02", "市民中心")}
    trip_ids: dict[str, int] = {}
    for trip_no, vehicle, offset in specs:
        trip = Trip(line_id=line.id, trip_no=trip_no, planned_depart=base + timedelta(minutes=offset), vehicle_no=vehicle)
        db.add(trip); db.flush()
        trip_ids[trip_no] = trip.id
        for seq, stop in enumerate(stops):
            arrive = base + timedelta(minutes=offset + seq * 6)
            if stop == "市民中心" and trip_no == "T02":
                arrive = base + timedelta(minutes=8)
            if stop == "火车站" and trip_no == "T03":
                arrive = base + timedelta(minutes=30)
            db.add(Arrival(trip_id=trip.id, stop_name=stop, stop_seq=seq, actual_arrive=arrive))
    db.flush()
    for trip_no, stop in skip_specs:
        db.add(SkipStop(trip_id=trip_ids[trip_no], stop_name=stop))
    db.commit()
