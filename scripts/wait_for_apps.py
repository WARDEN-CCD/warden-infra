"""Wait until every Argo CD Application is Synced and Healthy.

  python scripts/wait_for_apps.py [--min-apps N] [--timeout SECONDS]

Polls `kubectl get applications -n argocd`. Succeeds when at least --min-apps exist and all are Synced/Healthy on
two consecutive polls (ApplicationSets create apps gradually). On timeout prints what is still unhealthy and exits 1.
Stdlib only.
"""

import argparse
import json
import subprocess
import sys
import time


def applications() -> list[dict]:
    out = subprocess.run(["kubectl", "get", "applications.argoproj.io", "-n", "argocd", "-o", "json"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return []
    return json.loads(out.stdout).get("items", [])


def state(app: dict) -> tuple[str, str, str]:
    status = app.get("status", {})
    sync = status.get("sync", {}).get("status", "Unknown")
    health = status.get("health", {}).get("status", "Unknown")
    message = ""
    for cond in status.get("conditions", []) or []:
        message = cond.get("message", "")
    op = status.get("operationState", {})
    if op.get("phase") in ("Failed", "Error"):
        message = op.get("message", message)
    return sync, health, message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-apps", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    good_polls = 0
    last = ""
    while time.time() < deadline:
        apps = applications()
        rows = [(a["metadata"]["name"], *state(a)) for a in apps]
        bad = [r for r in rows if r[1] != "Synced" or r[2] != "Healthy"]
        summary = f"{len(rows) - len(bad)}/{len(rows)} apps Synced+Healthy"
        if summary != last:
            print(f"[{time.strftime('%H:%M:%S')}] {summary}" + (f"; waiting on {', '.join(r[0] for r in bad)}" if bad else ""),
                  flush=True)
            last = summary
        good_polls = good_polls + 1 if rows and not bad and len(rows) >= args.min_apps else 0
        if good_polls >= 2:
            return 0
        time.sleep(15)

    print("Timed out. Not ready:")
    for name, sync, health, message in [(a["metadata"]["name"], *state(a)) for a in applications()]:
        if sync != "Synced" or health != "Healthy":
            print(f"  {name}: sync={sync} health={health} {message[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
