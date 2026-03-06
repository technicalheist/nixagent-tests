import sys

def setup_stdout_encoding():
    # Force UTF-8 output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def banner(text: str) -> None:
    line = "=" * 70
    print(f"\n{line}\n  {text}\n{line}")

def section(text: str) -> None:
    print(f"\n{'─' * 60}\n  {text}\n{'─' * 60}")
