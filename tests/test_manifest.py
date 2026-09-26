"""Recovery manifest + checksum helper."""
import hashlib
import json

import manifest


def test_sha256_matches_hashlib(tmp_path):
    p = tmp_path / "f.bin"
    data = b"reclaim" * 1000
    p.write_bytes(data)
    assert manifest.sha256(str(p)) == hashlib.sha256(data).hexdigest()


def test_sha256_missing_file_returns_none(tmp_path):
    assert manifest.sha256(str(tmp_path / "nope.bin")) is None


def test_write_shape(tmp_path):
    entries = [{"n": 1, "file": "videos/clip_001.mp4", "size": 123, "sha256": "abc"}]
    path = manifest.write(str(tmp_path), "recover-videos", "/dev/sdb", entries,
                          extra={"playable": 1})
    payload = json.load(open(path))
    assert payload["tool"] == "recover-videos"
    assert payload["count"] == 1
    assert payload["playable"] == 1
    assert payload["entries"] == entries
    assert payload["source"] == "/dev/sdb"
    assert "created" in payload
