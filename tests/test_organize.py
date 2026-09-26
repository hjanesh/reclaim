"""Pure helpers in organize.py (date bucketing + collision-safe naming)."""
import datetime
import os

import organize


def test_mtime_date_iso(tmp_path):
    p = tmp_path / "f.arw"
    p.write_bytes(b"x")
    os.utime(p, (0, 0))   # epoch -> 1970-01-01 in local tz (or 1969-12-31 west of UTC)
    assert organize.mtime_date(str(p)) in ("1970-01-01", "1969-12-31")


def test_mtime_date_roundtrip(tmp_path):
    p = tmp_path / "f.arw"
    p.write_bytes(b"x")
    ts = datetime.datetime(2023, 6, 15, 12, 0, 0).timestamp()
    os.utime(p, (ts, ts))
    assert organize.mtime_date(str(p)) == "2023-06-15"


def test_relabel_map_sony_raw():
    # carved Sony RAW extensions normalize to .arw
    for src in ("sr2", "srf", "tif", "tiff"):
        assert organize.RELABEL[src] == "arw"


def test_unique_increments_on_collision(tmp_path):
    p = tmp_path / "a.jpg"
    p.write_bytes(b"x")
    assert organize.unique(str(p)) == str(tmp_path / "a_1.jpg")
