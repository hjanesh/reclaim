"""The append-only audit log used to surface previously-silent failures."""
import importlib

import runlog


def _fresh():
    # runlog holds module-level state (_path); reset it between tests
    importlib.reload(runlog)
    return runlog


def test_warn_writes_line(tmp_path):
    rl = _fresh()
    rl.set_dir(str(tmp_path))
    rl.warn("something odd", ValueError("boom"))
    log = (tmp_path / "reclaim.log").read_text()
    assert "WARN" in log and "something odd" in log and "ValueError: boom" in log


def test_levels(tmp_path):
    rl = _fresh()
    rl.set_dir(str(tmp_path))
    rl.info("started")
    rl.error("bad", OSError("nope"))
    log = (tmp_path / "reclaim.log").read_text().splitlines()
    assert any("INFO" in line and "started" in line for line in log)
    assert any("ERROR" in line and "OSError: nope" in line for line in log)


def test_noop_without_dir(tmp_path):
    rl = _fresh()
    # never called set_dir -> must not raise, must not create anything
    rl.warn("dropped")
    assert not (tmp_path / "reclaim.log").exists()
