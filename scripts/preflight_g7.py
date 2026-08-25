from _g5_cli import read_only_preflight, run_cli

def preflight_g7(root=None):
    return read_only_preflight(root, gate="G7") if root is not None else read_only_preflight(gate="G7")

if __name__ == "__main__":
    raise SystemExit(run_cli("preflight_g7", blocked_reason="G7 is not authorized during current G5 gate"))
