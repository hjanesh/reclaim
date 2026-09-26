"""ANSI-aware width helpers in theme.py. Easy to break, used by every panel."""
import theme as T


def test_vlen_ignores_ansi():
    s = T.fg(T.GREEN) + "hello" + T.RESET
    assert T.vlen(s) == 5


def test_vlen_plain():
    assert T.vlen("abcdef") == 6


def test_trunc_cuts_visible_chars():
    s = T.fg(T.CYAN) + "abcdef" + T.RESET
    out = T.trunc(s, 3)
    assert T.vlen(out) == 3


def test_trunc_shorter_than_limit_unchanged_visible():
    s = "abc"
    assert T.vlen(T.trunc(s, 10)) == 3


def test_human_fixed_width():
    assert T.human(0).endswith("B ")
    assert T.human(1024).strip() == "1.0 KB"
    assert T.human(1536).strip() == "1.5 KB"
    assert T.human(1024 ** 3).strip() == "1.0 GB"


def test_human_t_strips_padding():
    assert T.human_t(1024) == "1.0 KB"
    assert not T.human_t(1024).startswith(" ")   # leading pad trimmed
    assert T.human(1024).startswith(" ")          # human() keeps fixed width


def test_hbar_visible_width_matches_request():
    assert T.vlen(T.hbar(0.5, 20, T.GREEN)) == 20
    assert T.vlen(T.hbar(0.0, 12, T.GREEN)) == 12
    assert T.vlen(T.hbar(1.0, 8, T.GREEN)) == 8


def test_hbar_clamps_out_of_range():
    # frac > 1 and < 0 must not blow the width
    assert T.vlen(T.hbar(5.0, 10, T.GREEN)) == 10
    assert T.vlen(T.hbar(-2.0, 10, T.GREEN)) == 10


def test_gradient_bar_width():
    assert T.vlen(T.gradient_bar(0.5, 16)) == 16
