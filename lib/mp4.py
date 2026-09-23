#!/usr/bin/env python3
"""
mp4.py — MP4/MOV (ISO base media / QuickTime) atom logic. No UI.

Shared by the video scanner (detection dashboard) and the video recoverer
(carver). All reads are read-only. A "clip" starts at an `ftyp` box; we walk
the top-level atom chain to measure its extent and decide whether it's
complete (has moov + mdat) or truncated/fragmented.
"""
import os
import json

# recognised top-level atom types
TOP = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"uuid",
       b"meta", b"pnot", b"udta", b"mfra"}

MIN_CLIP = 512 * 1024          # ignore sub-512KB false hits


def walk(f, start, img_size):
    """
    Walk the atom chain from an ftyp start.
    Returns dict: {off, size, moov, mdat, brand, state}.
    state ∈ {'complete','trunc','fragment'}.
    """
    off = start
    moov = mdat = False
    brand = "?"
    first = True
    while off < img_size:
        f.seek(off)
        hdr = f.read(16)
        if len(hdr) < 8:
            break
        size = int.from_bytes(hdr[0:4], "big")
        typ = hdr[4:8]
        if typ not in TOP:
            break                       # chain ends / fragmentation boundary
        if size == 1:                   # 64-bit largesize
            size = int.from_bytes(hdr[8:16], "big")
        elif size == 0:                 # extends to EOF
            size = img_size - off
        if size < 8 or off + size > img_size + 8:
            break
        if first and typ == b"ftyp":
            brand = hdr[8:12].decode("latin1", "replace").strip()
        if typ == b"moov":
            moov = True
        if typ == b"mdat":
            mdat = True
        off += size
        first = False
    size = off - start
    if moov and mdat:
        state = "complete"
    elif mdat:
        state = "trunc"
    else:
        state = "fragment"
    return {"off": start, "size": size, "moov": moov, "mdat": mdat,
            "brand": brand, "state": state}


def is_ftyp_candidate(data, j):
    """Validate an 'ftyp' hit at index j in `data` (needs the 4 size bytes before)."""
    if j < 4:
        return False
    boxsize = int.from_bytes(data[j - 4:j], "big")
    if not (16 <= boxsize <= 64):
        return False
    if j + 8 > len(data):
        return False
    return all(32 <= b < 127 for b in data[j + 4:j + 8])   # printable major brand


def scan(image, limit=None, chunk=16 * 1024 * 1024, progress=None):
    """
    Generator. Scans `image` for clips up to `limit` bytes.
    Yields the walk() dict for each clip >= MIN_CLIP.
    `progress(pos, count)` called periodically if provided.
    """
    img_size = os.path.getsize(image)
    if limit is None:
        limit = img_size
    limit = min(limit, img_size)
    count = 0
    with open(image, "rb") as f:
        read_pos = 0
        carry = b""
        while read_pos < limit:
            f.seek(read_pos)
            buf = f.read(min(chunk, int(limit) - read_pos))
            if not buf:
                break
            data = carry + buf
            base = read_pos - len(carry)
            i = 0
            while True:
                j = data.find(b"ftyp", i)
                if j < 0:
                    break
                if is_ftyp_candidate(data, j):
                    off = base + (j - 4)
                    clip = walk(f, off, img_size)
                    if clip["size"] >= MIN_CLIP:
                        count += 1
                        yield clip
                i = j + 4
            carry = data[-8:]
            read_pos += len(buf)
            if progress:
                progress(read_pos, count)


def carve(image, off, size, out_path, chunk=8 * 1024 * 1024):
    """Copy `size` bytes at `off` from `image` to `out_path` (read-only source)."""
    written = 0
    with open(image, "rb") as src, open(out_path, "wb") as dst:
        src.seek(off)
        while written < size:
            buf = src.read(min(chunk, size - written))
            if not buf:
                break
            dst.write(buf)
            written += len(buf)
    return written


# ---------------------------------------------------------------------------
# Clip-table cache — lets "Detect" save results that "Recover" reuses later,
# so you can scan today and recover another day without re-scanning.
# ---------------------------------------------------------------------------
def cache_path(image):
    return image + ".clips.json"


def save_clips(image, clips, scanned_bytes):
    """Write the detected clip table beside the image."""
    try:
        payload = {
            "image": os.path.abspath(image),
            "image_size": os.path.getsize(image),
            "scanned_bytes": int(scanned_bytes),
            "clips": clips,
        }
        with open(cache_path(image), "w") as f:
            json.dump(payload, f)
        return True
    except OSError:
        return False


def load_clips(image):
    """Return (clips, scanned_bytes) from a valid cache, or (None, 0)."""
    p = cache_path(image)
    if not os.path.exists(p):
        return None, 0
    try:
        with open(p) as f:
            data = json.load(f)
        # invalidate if the image changed size (different image)
        if data.get("image_size") != os.path.getsize(image):
            return None, 0
        return data.get("clips"), data.get("scanned_bytes", 0)
    except (OSError, ValueError):
        return None, 0
