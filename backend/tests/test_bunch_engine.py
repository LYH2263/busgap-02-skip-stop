from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching

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

def test_skipped_trip_removed_from_stop_pairs():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    # T2 在 A 站越站：T1/T3 直接相邻，且没有任何事件以 T2 为端点
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, skipped={("T2", "A")})
    assert len(events) == 1
    assert events[0].earlier_trip == "T1"
    assert events[0].later_trip == "T3"
    assert events[0].gap_min == 20.0
    assert events[0].status == "large_gap"

def test_skipped_only_at_named_stop():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "B", "trip_no": "T1", "actual_arrive": base + timedelta(minutes=10)},
        {"stop_name": "B", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=12)},
    ]
    # 只在 A 站越站，B 站 T2 照常参与
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, skipped={("T2", "A")})
    assert len(events) == 1
    assert events[0].stop_name == "B"
    assert (events[0].earlier_trip, events[0].later_trip) == ("T1", "T2")
