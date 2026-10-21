"""Rebuild ledger writer (EVALUATION.md E6).

  python scripts/ledger.py start <env>
  python scripts/ledger.py finish <env> <exit_code> [profile] [notes]

`start` records a timestamp; `finish` appends one row to the hub's evidence/rebuilds/rebuild-ledger.csv with
the duration and the commit of each platform repo. Stdlib only. Hub location: $WARDEN_HUB or the parent folder.
"""

import csv
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HUB = Path(os.environ.get("WARDEN_HUB", REPO.parent))
LEDGER = HUB / "evidence" / "rebuilds" / "rebuild-ledger.csv"
REPOS = ["warden-infra", "warden-gitops", "warden-policy", "warden-platform"]


def sha(repo: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(HUB / repo), "rev-parse", "--short=12", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(HUB / repo), "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        return out + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "none"


def operator() -> str:
    res = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
    return res.stdout.strip() or "unknown"


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in ("start", "finish"):
        print(__doc__)
        return 2
    action, env = sys.argv[1], sys.argv[2]
    marker = REPO / f".ledger-{env}.start"

    if action == "start":
        marker.write_text(str(time.time()))
        return 0

    exit_code = sys.argv[3] if len(sys.argv) > 3 else "0"
    profile = sys.argv[4] if len(sys.argv) > 4 else "lite"
    notes = sys.argv[5] if len(sys.argv) > 5 else ""
    started = float(marker.read_text()) if marker.exists() else time.time()
    marker.unlink(missing_ok=True)

    row = [
        dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        env, profile, *(sha(r) for r in REPOS),
        round(time.time() - started), "ok" if exit_code == "0" else f"failed({exit_code})",
        operator(), notes,
    ]
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(row)
    print(f"ledger: {env} {row[8]} in {row[7]} s -> {LEDGER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
