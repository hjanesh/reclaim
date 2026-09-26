"""Truth table for the unified path-safety guard (the whole point of Tier 1)."""
import safety


def test_identical_paths_rejected(tmp_path):
    d = str(tmp_path / "same")
    ok, reason = safety.check_output(d, d)
    assert not ok and "same path" in reason


def test_output_inside_source_rejected(tmp_path):
    src = tmp_path / "src"
    out = src / "recovered"
    ok, reason = safety.check_output(str(src), str(out))
    assert not ok and "inside the source" in reason


def test_source_inside_output_rejected(tmp_path):
    out = tmp_path / "out"
    src = out / "card.img"
    ok, reason = safety.check_output(str(src), str(out))
    assert not ok and "source is inside" in reason


def test_sibling_paths_allowed(tmp_path):
    ok, reason = safety.check_output(str(tmp_path / "src"), str(tmp_path / "dst"))
    assert ok and reason == ""


def test_prefix_lookalike_not_treated_as_nested(tmp_path):
    # 'photos_backup' must not count as inside 'photos' (commonpath, not startswith)
    ok, _ = safety.check_output(str(tmp_path / "photos"), str(tmp_path / "photos_backup"))
    assert ok


def test_device_source_only_needs_distinct_path():
    # /dev/sdb as source vs a normal output dir -> path containment N/A, allowed
    ok, _ = safety.check_output("/dev/sdb", "/home/user/output/photos")
    assert ok


def test_device_equal_to_itself_rejected():
    ok, reason = safety.check_output("/dev/sdb", "/dev/sdb")
    assert not ok and "same path" in reason


def test_is_device():
    assert safety.is_device("/dev/sdb")
    assert safety.is_device("/dev/disk4")
    assert not safety.is_device("/home/user/card.img")
