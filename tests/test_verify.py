"""Pure logic in verify.py: classification + content-hash de-dup grouping.

The ffprobe/exiftool probes need external tools + real media, so they're not
unit-tested here; classify() and find_duplicates() carry the logic that matters.
"""
import verify


def test_classify():
    assert verify.classify("mp4") == "video"
    assert verify.classify("mov") == "video"
    assert verify.classify("arw") == "photo"
    assert verify.classify("jpg") == "photo"
    assert verify.classify("txt") == "other"


def test_find_duplicates_groups_identical_content(tmp_path):
    # three files, two identical -> one duplicate group of two
    (tmp_path / "a.jpg").write_bytes(b"same-bytes")
    (tmp_path / "b.jpg").write_bytes(b"same-bytes")
    (tmp_path / "c.jpg").write_bytes(b"different")
    dups = verify.find_duplicates(str(tmp_path))
    assert len(dups) == 1
    (group,) = dups.values()
    assert len(group) == 2
    assert group == sorted(group)   # deterministic order (first kept on --apply)


def test_find_duplicates_none_when_all_unique(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"one")
    (tmp_path / "b.jpg").write_bytes(b"two")
    assert verify.find_duplicates(str(tmp_path)) == {}


def test_find_duplicates_ignores_non_media(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"dup")
    (tmp_path / "b.txt").write_bytes(b"dup")   # not media -> not grouped
    assert verify.find_duplicates(str(tmp_path)) == {}
