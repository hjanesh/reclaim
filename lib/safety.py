#!/usr/bin/env python3
"""
safety.py - one place for the "never clobber the source" rules. No UI, no deps.

Reclaim's golden rule is that a recovery must never write into (or over) the
thing it's reading from. Historically that check lived in three different ad-hoc
spots that each caught a different subset of the danger. This module is the
single source of truth: `check_output(source, out)` rejects a destination that
equals the source OR nests with it in either direction. Pure functions only, so
it's trivially testable and safe to import anywhere.
"""
import os


def _norm(p):
    """Absolute, symlink-resolved, ~ and $VAR expanded. Works for paths that
    don't exist yet (resolves the existing parent, keeps the rest)."""
    return os.path.realpath(os.path.abspath(os.path.expanduser(os.path.expandvars(str(p)))))


def is_device(source):
    """A raw device node (imaging source) rather than a file/dir path."""
    return str(source).startswith("/dev/")


def _within(child, parent):
    """True if `child` is the same as, or nested under, `parent`.
    Uses commonpath so 'foobar' is NOT treated as inside 'foo'."""
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False   # different drives / mixed abs+rel → not nested


def check_output(source, out):
    """
    Validate that `out` is a safe place to write given `source`.
    Returns (ok: bool, reason: str). reason is "" when ok.

    Rejected: identical paths; out inside source; source inside out.
    Device sources (/dev/...) can't contain a filesystem path, so only the
    identity check applies here (same PHYSICAL device is a separate check in
    platform_utils.same_device, since /dev/sdb and /dev/sdb1 differ as strings).
    """
    s = _norm(source)
    o = _norm(out)
    if s == o:
        return False, "destination is the same path as the source"
    if not is_device(source):
        if _within(o, s):
            return False, "destination is inside the source folder"
        if _within(s, o):
            return False, "source is inside the destination folder"
    return True, ""
