from _g5_cli import run_cli


def main() -> int:
    return run_cli("resume_g6_jobs", blocked_reason="formal G6 recovery is not authorized")


if __name__ == "__main__":
    raise SystemExit(main())
