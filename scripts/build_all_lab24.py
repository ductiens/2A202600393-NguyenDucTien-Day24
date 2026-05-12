"""One-command builder for all Lab 24 submission artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print(f"> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    py = sys.executable
    run([py, "scripts/build_phase_a.py"])
    run([py, "scripts/build_phase_b.py"])
    run([py, "scripts/build_phase_c.py"])
    run([py, "scripts/build_bonus_cross_judge.py"])
    run([py, "phase-b/kappa_analysis.py"])
    print("All Lab 24 artifacts generated successfully.")


if __name__ == "__main__":
    main()
