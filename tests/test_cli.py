"""Non-interactive CLI: argument parsing + dispatch to the lib scripts."""
import reclaim


def test_no_args_is_menu():
    args = reclaim.build_parser().parse_args([])
    assert args.cmd is None   # main() routes None -> interactive menu


def test_detect_args():
    args = reclaim.build_parser().parse_args(["detect", "card.img", "5"])
    assert args.cmd == "detect" and args.image == "card.img" and args.gb == "5"


def test_detect_gb_default():
    args = reclaim.build_parser().parse_args(["detect", "card.img"])
    assert args.gb == "60"


def test_recover_flags():
    args = reclaim.build_parser().parse_args(
        ["recover", "c.img", "out", "--ref", "refs/", "--gb", "20"])
    assert args.cmd == "recover" and args.ref == "refs/" and args.gb == "20"


def test_organize_apply_flag():
    args = reclaim.build_parser().parse_args(["organize", "src", "out", "--apply"])
    assert args.cmd == "organize" and args.apply is True
    args = reclaim.build_parser().parse_args(["organize", "src", "out"])
    assert args.apply is False


def test_verify_flags():
    args = reclaim.build_parser().parse_args(["verify", "folder", "--dedup", "--apply"])
    assert args.cmd == "verify" and args.dedup and args.apply


# --- dispatch wires the right lib script + args --------------------------
def test_cli_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(reclaim, "run_py", lambda *a: calls.append(a))

    reclaim.cli(reclaim.build_parser().parse_args(["detect", "c.img", "7"]))
    assert calls[-1] == ("scan_mp4.py", "c.img", "7")

    reclaim.cli(reclaim.build_parser().parse_args(["recover", "c.img", "o", "--gb", "3"]))
    assert calls[-1] == ("video_recover.py", "c.img", "o", "", "3")

    reclaim.cli(reclaim.build_parser().parse_args(["rename", "s", "o", "--apply"]))
    assert calls[-1] == ("rename.py", "s", "o", "--apply")

    reclaim.cli(reclaim.build_parser().parse_args(["verify", "f", "--dedup"]))
    assert calls[-1] == ("verify.py", "f", "--dedup")
