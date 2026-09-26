#!/usr/bin/env python3
"""
runlog.py - tiny append-only audit log for a recovery run. No UI, no deps.

Recovery is long, unattended, and full of best-effort steps that used to fail
silently (`except Exception: pass`). This records those non-fatal hiccups to a
plain-text log in the active output directory so there's an audit trail of what
actually happened, without cluttering the live dashboard.

Usage:
    import runlog
    runlog.set_dir(out_dir)          # once, per run
    runlog.warn("untrunc failed on clip_007", exc)
"""
import os
import time

_path = None


def set_dir(out_dir):
    """Point the log at <out_dir>/reclaim.log. Safe to call repeatedly."""
    global _path
    try:
        os.makedirs(out_dir, exist_ok=True)
        _path = os.path.join(out_dir, "reclaim.log")
    except OSError:
        _path = None


def _write(level, msg, exc=None):
    if not _path:
        return
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {level:<5} {msg}"
    if exc is not None:
        line += f"  ({type(exc).__name__}: {exc})"
    try:
        with open(_path, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def info(msg):            _write("INFO", msg)
def warn(msg, exc=None):  _write("WARN", msg, exc)
def error(msg, exc=None): _write("ERROR", msg, exc)
