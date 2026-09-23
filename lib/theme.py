#!/usr/bin/env python3
"""
theme.py — shared terminal UI for Reclaim.

One place for the look-and-feel used by every dashboard and the main menu:
true-colour palette, ANSI-safe width helpers, bordered panels, a stable
no-scroll live redraw, block/heatmap bars, and themed interactive prompts.

Pure stdlib. No side effects on import.
"""
import sys, os, shutil

RESET = "\x1b[0m"

# ---- palette (RGB) ----
GREEN  = (46, 204, 113)     # rescued / complete / go
SLATE  = (44, 48, 58)       # pending / scanned-empty
DARK   = (30, 33, 40)       # not-yet / empty
YELLOW = (241, 196, 15)     # truncated / audio
ORANGE = (230, 126, 34)     # non-scraped / warn
RED    = (231, 76, 60)      # bad / error
CYAN   = (26, 232, 255)     # active head / accent
BLUE   = (52, 152, 219)     # jpeg
PURPLE = (155, 89, 182)     # video
BORDER = (78, 92, 120)      # frame
TITLE  = (236, 240, 245)    # bright text
MUTED  = (120, 128, 140)    # dim text
BAR    = [(18, 64, 40), (33, 140, 82), (46, 204, 113), (130, 255, 175)]  # loader gradient


def fg(c): return f"\x1b[38;2;{c[0]};{c[1]};{c[2]}m"
def bg(c): return f"\x1b[48;2;{c[0]};{c[1]};{c[2]}m"
def paint(c, s): return fg(c) + s + RESET
def chip(c): return bg(c) + "  " + RESET
def bold(s): return "\x1b[1m" + s + RESET


def human(n):
    """Human-readable bytes, fixed width."""
    n = float(n)
    for u in ("B ", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:6.1f} {u}"
        n /= 1024.0


def human_t(n):
    """Human-readable bytes, trimmed (no padding)."""
    return human(n).strip()


def vlen(s):
    """Visible length of a string, ignoring ANSI escapes."""
    out = i = 0
    while i < len(s):
        if s[i] == "\x1b":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
        else:
            out += 1; i += 1
    return out


def trunc(s, n):
    """Cut a string to n visible chars, preserving ANSI codes."""
    out = []; c = i = 0
    while i < len(s):
        if s[i] == "\x1b":
            j = i
            while j < len(s) and s[j] != "m":
                j += 1
            out.append(s[i:j + 1]); i = j + 1
        else:
            if c >= n:
                break
            out.append(s[i]); c += 1; i += 1
    return "".join(out) + RESET


def term():
    """(cols, rows) of the terminal, with a sane fallback."""
    s = shutil.get_terminal_size((84, 30))
    return s.columns, s.lines


def bar_col(t):
    """Colour along the loader gradient for fraction t in [0,1]."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    x = t * (len(BAR) - 1); i = int(x); f = x - i
    if i >= len(BAR) - 1:
        return BAR[-1]
    a, b = BAR[i], BAR[i + 1]
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


def hbar(frac, width, col, empty=(40, 44, 54), char="█", echar="─"):
    """Horizontal bar: filled `col` blocks + dim remainder."""
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    f = int(round(width * frac))
    return fg(col) + char * f + fg(empty) + echar * (width - f) + RESET


def gradient_bar(frac, width):
    """Loader bar using the green gradient."""
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    f = int(round(width * frac))
    out = []
    for i in range(width):
        if i < f:
            out.append(fg(bar_col(0.35 + 0.6 * (i / max(1, f)))) + "█")
        else:
            out.append(fg((40, 44, 54)) + "─")
    return "".join(out) + RESET


# ---------------------------------------------------------------------------
# Panels (bordered, fixed-width, ANSI-safe)
# ---------------------------------------------------------------------------
def panel_top(W, title=None, subtitle=None):
    top = fg(BORDER) + "┌" + "─" * W + "┐" + RESET
    if title is None:
        return [top]
    inner = "  " + bold(fg(TITLE) + title + RESET)
    if subtitle:
        inner += fg(MUTED) + "  ·  " + subtitle + RESET
    return [top, panel_row(inner, W), panel_sep(W)]


def panel_row(inner, W):
    inner = trunc(inner, W)
    return fg(BORDER) + "│" + RESET + inner + " " * (W - vlen(inner)) + fg(BORDER) + "│" + RESET


def panel_sep(W):
    return fg(BORDER) + "├" + "─" * W + "┤" + RESET


def panel_bot(W):
    return fg(BORDER) + "└" + "─" * W + "┘" + RESET


# ---------------------------------------------------------------------------
# Live (stable, no-scroll redraw)
# ---------------------------------------------------------------------------
class Live:
    """Context manager for a flicker-free, non-scrolling live display."""
    def __enter__(self):
        sys.stdout.write("\x1b[?25l\x1b[2J")   # hide cursor, clear
        sys.stdout.flush()
        return self

    def frame(self, lines):
        sys.stdout.write("\x1b[H" + "\n".join(ln + "\x1b[K" for ln in lines) + "\x1b[J")
        sys.stdout.flush()

    def __exit__(self, *a):
        sys.stdout.write("\x1b[?25h\n")
        sys.stdout.flush()
        return False


# ---------------------------------------------------------------------------
# Static output helpers
# ---------------------------------------------------------------------------
def clear():
    sys.stdout.write("\x1b[2J\x1b[H"); sys.stdout.flush()

def rule(text="", W=None):
    W = W or min(term()[0] - 2, 78)
    if text:
        t = f" {text} "
        pad = W - vlen(t)
        print(fg(BORDER) + "─── " + RESET + bold(fg(TITLE) + text + RESET) +
              " " + fg(BORDER) + "─" * max(0, pad - 4) + RESET)
    else:
        print(fg(BORDER) + "─" * W + RESET)

def info(msg): print(fg(CYAN) + "  ›  " + RESET + msg)
def ok(msg):   print(fg(GREEN) + "  ✔  " + RESET + msg)
def warn(msg): print(fg(YELLOW) + "  ⚠  " + RESET + msg)
def err(msg):  print(fg(RED) + "  ✖  " + RESET + msg)

def banner(title, subtitle=None):
    W = min(term()[0] - 2, 78)
    for ln in panel_top(W, title, subtitle):
        print(ln)
    print(panel_bot(W))


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------
def menu(title, items, subtitle=None):
    """
    Render a themed menu. `items` = list of (key, label, desc).
    Returns the chosen key (str). Loops until a valid key is entered.
    """
    W = min(term()[0] - 2, 78)
    while True:
        clear()
        for ln in panel_top(W, title, subtitle):
            print(ln)
        for key, label, desc in items:
            left = f"  {fg(CYAN)}{bold(key)}{RESET})  {fg(TITLE)}{label}{RESET}"
            print(panel_row(left, W))
            if desc:
                print(panel_row(f"       {fg(MUTED)}{desc}{RESET}", W))
        print(panel_bot(W))
        choice = input(fg(CYAN) + "  select ▸ " + RESET).strip()
        for key, _, _ in items:
            if choice.lower() == key.lower():
                return key
        err("invalid choice — try again"); input("  (enter to continue)")


def ask(q, default=None):
    suffix = f" {fg(MUTED)}[{default}]{RESET}" if default is not None else ""
    val = input(fg(CYAN) + "  ? " + RESET + q + suffix + fg(CYAN) + " ▸ " + RESET).strip()
    return val or (default if default is not None else "")


def ask_path(q, must_exist=True, want="any", default=None):
    """
    Ask for a filesystem path. want in {'any','file','dir'}.
    Expands ~ and $VARS. Re-prompts until valid (or blank if allowed).
    """
    while True:
        raw = ask(q, default)
        if not raw:
            if default is None and not must_exist:
                return ""
            err("please enter a path"); continue
        p = os.path.abspath(os.path.expanduser(os.path.expandvars(raw)))
        if not must_exist:
            return p
        if not os.path.exists(p):
            err(f"not found: {p}"); continue
        if want == "file" and not os.path.isfile(p):
            err("that is not a file"); continue
        if want == "dir" and not os.path.isdir(p):
            err("that is not a directory"); continue
        return p


def confirm(q, default=False):
    d = "Y/n" if default else "y/N"
    val = input(fg(CYAN) + "  ? " + RESET + q + f" {fg(MUTED)}[{d}]{RESET}" +
                fg(CYAN) + " ▸ " + RESET).strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


def pause(msg="press enter to continue"):
    input(fg(MUTED) + f"  {msg} … " + RESET)
