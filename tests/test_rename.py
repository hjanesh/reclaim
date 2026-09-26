"""Filename-restoration logic in rename.py (pure; no exiftool needed)."""
import rename


# --- embedded_name: use the on-card name only when it's clean & plausible ---
def test_embedded_name_from_original_filename():
    assert rename.embedded_name({"OriginalFileName": "DSC01234.ARW"}) == "DSC01234"


def test_embedded_name_strips_windows_path():
    assert rename.embedded_name({"PreservedFileName": r"A:\DCIM\IMG_0042.JPG"}) == "IMG_0042"


def test_embedded_name_empty_when_absent():
    assert rename.embedded_name({}) == ""


def test_embedded_name_strips_path_traversal():
    # only the basename is kept, so a traversal payload can't escape the out dir
    assert rename.embedded_name({"OriginalFileName": "../../etc/passwd"}) == "passwd"


def test_embedded_name_rejects_unsafe_chars():
    assert rename.embedded_name({"OriginalFileName": "bad name*?.arw"}) == ""


def test_embedded_name_rejects_overlong():
    long = "A" * 80 + ".arw"
    assert rename.embedded_name({"OriginalFileName": long}) == ""


# --- reconstructed_name: build a clean name from time + model ---------------
def test_reconstructed_sony_prefix():
    row = {"DateTimeOriginal": "20230101_120000", "Model": "ILCE-7M3"}
    assert rename.reconstructed_name(row, "fallback") == "DSC_20230101_120000"


def test_reconstructed_generic_prefix():
    row = {"CreateDate": "20230101_120000", "Model": "Canon EOS R5"}
    assert rename.reconstructed_name(row, "fallback") == "IMG_20230101_120000"


def test_reconstructed_appends_subsec():
    row = {"DateTimeOriginal": "20230101_120000", "Model": "ILCE-7M3",
           "SubSecTimeOriginal": "42"}
    assert rename.reconstructed_name(row, "fallback") == "DSC_20230101_120000_42"


def test_reconstructed_falls_back_without_date():
    assert rename.reconstructed_name({"Model": "ILCE-7M3"}, "fallback") == "fallback"


# --- unique(): never clobber an existing target -----------------------------
def test_unique_returns_path_when_free(tmp_path):
    p = str(tmp_path / "a.arw")
    assert rename.unique(p) == p


def test_unique_increments_on_collision(tmp_path):
    p = tmp_path / "a.arw"
    p.write_bytes(b"x")
    assert rename.unique(str(p)) == str(tmp_path / "a_1.arw")
    (tmp_path / "a_1.arw").write_bytes(b"x")
    assert rename.unique(str(p)) == str(tmp_path / "a_2.arw")
