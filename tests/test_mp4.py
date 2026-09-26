"""Unit tests for mp4.py atom logic against synthetic in-memory MP4 fixtures.

We build minimal but structurally-valid ISO-BMFF/QuickTime byte streams (a box
is: 4-byte big-endian size, 4-byte type, payload) so the tests need no real
video files and no external tools.
"""
import json
import os

import mp4


# --- fixture builders ------------------------------------------------------
def box(typ: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + typ + payload


def ftyp(brand: bytes = b"mp42") -> bytes:
    # major brand + minor version + one compatible brand => 20-byte box,
    # whose size (20) lands in is_ftyp_candidate's expected 16..64 window.
    return box(b"ftyp", brand + (0).to_bytes(4, "big") + b"mp42")


def styp(brand: bytes = b"msdh") -> bytes:
    return box(b"styp", brand + (0).to_bytes(4, "big") + b"msdh")


def moov(n: int = 32) -> bytes:
    return box(b"moov", b"\x00" * n)


def moof(n: int = 24) -> bytes:
    return box(b"moof", b"\x00" * n)


def mdat(n: int) -> bytes:
    return box(b"mdat", b"\xAB" * n)


def write(tmp_path, name, data: bytes) -> str:
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


# --- walk() classification -------------------------------------------------
def test_walk_complete(tmp_path):
    data = ftyp() + moov() + mdat(64)
    img = write(tmp_path, "complete.img", data)
    with open(img, "rb") as f:
        clip = mp4.walk(f, 0, len(data))
    assert clip["state"] == "complete"
    assert clip["moov"] and clip["mdat"]
    assert clip["brand"] == "mp42"
    assert clip["size"] == len(data)   # walked the whole contiguous chain


def test_walk_truncated_no_moov(tmp_path):
    data = ftyp() + mdat(64)
    img = write(tmp_path, "trunc.img", data)
    with open(img, "rb") as f:
        clip = mp4.walk(f, 0, len(data))
    assert clip["state"] == "trunc"
    assert clip["mdat"] and not clip["moov"]


def test_walk_fragment_ftyp_only(tmp_path):
    data = ftyp()
    img = write(tmp_path, "frag.img", data)
    with open(img, "rb") as f:
        clip = mp4.walk(f, 0, len(data))
    assert clip["state"] == "fragment"
    assert not clip["moov"] and not clip["mdat"]


def test_walk_stops_at_unknown_atom(tmp_path):
    # a junk atom after mdat is not in TOP -> chain ends there
    junk = box(b"JUNK", b"\x00" * 16)
    data = ftyp() + moov() + mdat(64) + junk
    img = write(tmp_path, "junk.img", data)
    with open(img, "rb") as f:
        clip = mp4.walk(f, 0, len(data))
    assert clip["state"] == "complete"
    assert clip["size"] == len(ftyp() + moov() + mdat(64))   # excludes JUNK


# --- fragmented / fMP4 (moof) + styp ---------------------------------------
def test_walk_fragmented_measures_full_extent(tmp_path):
    # ftyp + init moov + two (moof, mdat) fragments: walker must span all of it
    frag = moof() + mdat(64) + moof() + mdat(64)
    data = ftyp() + moov() + frag
    img = write(tmp_path, "frag.img", data)
    with open(img, "rb") as f:
        clip = mp4.walk(f, 0, len(data))
    assert clip["state"] == "complete"     # has the init moov
    assert clip["moof"] is True
    assert clip["size"] == len(data)       # did not stop at the first moof


def test_walk_styp_segment(tmp_path):
    # a DASH-style media segment: styp + moof + mdat (no top-level moov)
    data = styp() + moof() + mdat(64)
    img = write(tmp_path, "seg.img", data)
    with open(img, "rb") as f:
        clip = mp4.walk(f, 0, len(data))
    assert clip["moof"] and clip["mdat"] and not clip["moov"]
    assert clip["brand"] == "msdh"


def test_scan_finds_styp_anchored_clip(tmp_path):
    big = mp4.MIN_CLIP + 4096
    data = b"\x00" * 32 + styp() + moof() + mdat(big)
    img = write(tmp_path, "styp.img", data)
    clips = list(mp4.scan(img))
    assert len(clips) == 1
    assert clips[0]["off"] == 32


# --- is_ftyp_candidate() ---------------------------------------------------
def test_ftyp_candidate_accepts_valid():
    data = ftyp()
    j = data.find(b"ftyp")
    assert mp4.is_ftyp_candidate(data, j)


def test_ftyp_candidate_rejects_bad_size():
    # boxsize of 9 is outside the 16..64 window
    data = (9).to_bytes(4, "big") + b"ftyp" + b"mp42"
    assert not mp4.is_ftyp_candidate(data, 4)


def test_ftyp_candidate_rejects_nonprintable_brand():
    data = (20).to_bytes(4, "big") + b"ftyp" + b"\x00\x01\x02\x03"
    assert not mp4.is_ftyp_candidate(data, 4)


# --- scan() end to end (respects MIN_CLIP) ---------------------------------
def test_scan_finds_large_clip(tmp_path):
    big = mp4.MIN_CLIP + 4096
    data = b"\x00" * 128 + ftyp() + moov() + mdat(big) + b"\x00" * 64
    img = write(tmp_path, "scan.img", data)
    clips = list(mp4.scan(img))
    assert len(clips) == 1
    assert clips[0]["state"] == "complete"
    assert clips[0]["off"] == 128       # ftyp starts after the 128-byte pad


def test_scan_ignores_subthreshold_clip(tmp_path):
    data = ftyp() + moov() + mdat(1024)   # well under MIN_CLIP
    img = write(tmp_path, "small.img", data)
    assert list(mp4.scan(img)) == []


# --- carve() byte-exactness ------------------------------------------------
def test_carve_extracts_exact_bytes(tmp_path):
    payload = bytes(range(256)) * 40
    data = b"HEAD" + payload + b"TAIL"
    img = write(tmp_path, "src.img", data)
    out = str(tmp_path / "carved.bin")
    written = mp4.carve(img, 4, len(payload), out)
    assert written == len(payload)
    assert open(out, "rb").read() == payload


# --- clip cache round-trip -------------------------------------------------
def test_cache_save_and_load(tmp_path):
    img = write(tmp_path, "c.img", b"\x00" * 4096)
    clips = [{"off": 0, "size": 4096, "moov": True, "mdat": True,
              "brand": "mp42", "state": "complete"}]
    assert mp4.save_clips(img, clips, 4096)
    loaded, scanned = mp4.load_clips(img)
    assert loaded == clips and scanned == 4096
    assert os.path.exists(mp4.cache_path(img))


def test_cache_invalidated_on_size_change(tmp_path):
    img = write(tmp_path, "c.img", b"\x00" * 4096)
    mp4.save_clips(img, [{"off": 0, "size": 10}], 4096)
    # image grows -> cache no longer matches -> ignored
    with open(img, "ab") as f:
        f.write(b"\x00" * 10)
    loaded, scanned = mp4.load_clips(img)
    assert loaded is None and scanned == 0


def test_cache_missing_returns_none(tmp_path):
    img = write(tmp_path, "nocache.img", b"\x00" * 16)
    assert mp4.load_clips(img) == (None, 0)


def test_cache_payload_shape(tmp_path):
    img = write(tmp_path, "c.img", b"\x00" * 2048)
    mp4.save_clips(img, [], 2048)
    payload = json.load(open(mp4.cache_path(img)))
    assert payload["image_size"] == 2048
    assert payload["scanned_bytes"] == 2048
    assert payload["clips"] == []
