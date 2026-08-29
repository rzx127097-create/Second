from _g5_cli import read_only_preflight, run_cli


def preflight_g6(root=None):
    return read_only_preflight(root, gate="G6") if root is not None else read_only_preflight(gate="G6")


def main() -> int:
    return run_cli("preflight_g6", blocked_reason="G6 is not authorized during current G5 gate")


if __name__ == "__main__":
    raise SystemExit(main())
