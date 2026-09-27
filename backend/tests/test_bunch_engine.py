from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching, exclude_skipped

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

def test_skip_stop_removes_trip_from_that_stop_pairs():
    # T02 在市民中心越站：市民中心只剩 T01、T03，直接相邻（18 分钟，大间隔）；
    # 原 T01→T02 的 2 分钟串车配对消失。
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "市民中心", "trip_no": "T01", "actual_arrive": base},
        {"stop_name": "市民中心", "trip_no": "T02", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "市民中心", "trip_no": "T03", "actual_arrive": base + timedelta(minutes=18)},
    ]
    payload = exclude_skipped(arrivals, {"T02": {"市民中心"}})
    events = detect_bunching(payload, 8.0, 3.0, 15.0)
    assert [(e.earlier_trip, e.later_trip) for e in events] == [("T01", "T03")]
    assert events[0].gap_min == 18.0

def test_skip_one_stop_trip_still_participates_elsewhere():
    # T02 只越市民中心；在火车站它仍正常参与，T01→T02 串车仍在。
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "市民中心", "trip_no": "T01", "actual_arrive": base},
        {"stop_name": "市民中心", "trip_no": "T02", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "火车站", "trip_no": "T01", "actual_arrive": base + timedelta(minutes=6)},
        {"stop_name": "火车站", "trip_no": "T02", "actual_arrive": base + timedelta(minutes=8)},
    ]
    payload = exclude_skipped(arrivals, {"T02": {"市民中心"}})
    events = detect_bunching(payload, 8.0, 3.0, 15.0)
    by_stop = {e.stop_name: e for e in events}
    assert "市民中心" not in by_stop or by_stop["市民中心"].earlier_trip != "T01"
    assert (by_stop["火车站"].earlier_trip, by_stop["火车站"].later_trip) == ("T01", "T02")
    assert by_stop["火车站"].status == "bunching"
