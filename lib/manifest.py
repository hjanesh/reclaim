#!/usr/bin/env python3
"""
manifest.py - write a machine-readable record of a recovery run. No UI.

After a carve/repair pass you want to know, later and provably, what came out:
which clips, how big, what state, and a checksum to detect bit-rot or to
de-duplicate against another run. This drops a `manifest.json` in the output
directory. Pure stdlib; safe to import anywhere.
"""
import hashlib
import json
import os
import time


def sha256(path, chunk=1 << 20):
    """Streaming SHA-256 of a file, or None if it can't be read."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(chunk), b""):
                h.update(block)
    except OSError:
        return None
    return h.hexdigest()


def write(out_dir, tool, source, entries, extra=None):
    """
    Write <out_dir>/manifest.json describing the run.
    `entries` is a list of dicts (one per recovered file). Returns the path
    written, or None on failure.
    """
    payload = {
        "tool": tool,
        "source": os.path.abspath(source),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "count": len(entries),
        "entries": entries,
    }
    if extra:
        payload.update(extra)
    path = os.path.join(out_dir, "manifest.json")
    try:
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        return path
    except OSError:
        return None
