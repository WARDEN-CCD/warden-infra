"""Measure platform memory/CPU per component on the current cluster (spike S2, hub EVALUATION.md).

  python scripts/measure_memory.py [--samples 5] [--interval 30] [--out DIR]

Takes --samples readings of `kubectl top pods -A` (needs metrics-server) and `docker stats` for the kind node
containers, --interval seconds apart, and reports the median per namespace (one namespace per component).
Writes <out>/memory-<UTC timestamp>.json and prints a Markdown table. Stdlib only.
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO.parent / "evidence" / "spikes" / "S2"
UNITS = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024, "B": 1 / 1024 / 1024}


def run(*cmd: str) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def mib(value: str) -> float:
    m = re.match(r"([\d.]+)\s*([A-Za-z]+)", value.strip())
    return float(m.group(1)) * UNITS.get(m.group(2), 1) if m else 0.0


def pod_sample() -> dict[str, dict[str, float]]:
    per_ns: dict[str, dict[str, float]] = {}
    for line in run("kubectl", "top", "pods", "-A", "--no-headers").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        ns, _pod, cpu, mem = parts[:4]
        acc = per_ns.setdefault(ns, {"cpu_m": 0.0, "mem_mib": 0.0, "pods": 0})
        acc["cpu_m"] += float(cpu.rstrip("m")) if cpu.endswith("m") else float(cpu) * 1000
        acc["mem_mib"] += mib(mem)
        acc["pods"] += 1
    return per_ns


def node_sample() -> dict[str, float]:
    out = run("docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}")
    nodes = {}
    for line in out.splitlines():
        name, _, usage = line.partition("\t")
        if name.startswith("warden-"):
            nodes[name] = mib(usage.split("/")[0])
    return nodes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pods, nodes = [], []
    for i in range(args.samples):
        pods.append(pod_sample())
        nodes.append(node_sample())
        if i < args.samples - 1:
            time.sleep(args.interval)

    namespaces = sorted({ns for s in pods for ns in s})
    rows = []
    for ns in namespaces:
        mems = [s[ns]["mem_mib"] for s in pods if ns in s]
        cpus = [s[ns]["cpu_m"] for s in pods if ns in s]
        rows.append({"namespace": ns, "pods": max(s[ns]["pods"] for s in pods if ns in s),
                     "mem_mib_median": round(statistics.median(mems), 1), "mem_mib_max": round(max(mems), 1),
                     "cpu_m_median": round(statistics.median(cpus), 1)})
    rows.sort(key=lambda r: -r["mem_mib_median"])
    node_names = sorted({n for s in nodes for n in s})
    node_rows = [{"node": n, "mem_mib_median": round(statistics.median([s[n] for s in nodes if n in s]), 1)}
                 for n in node_names]

    result = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "samples": args.samples, "interval_s": args.interval,
        "pods_total_mem_mib_median": round(sum(r["mem_mib_median"] for r in rows), 1),
        "nodes_total_mem_mib_median": round(sum(r["mem_mib_median"] for r in node_rows), 1),
        "namespaces": rows, "nodes": node_rows,
        "kubectl_top_nodes": run("kubectl", "top", "nodes").strip().splitlines(),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"memory-{result['timestamp_utc'].replace(':', '')}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"| namespace | pods | memory MiB (median) | memory MiB (max) | CPU m (median) |")
    print(f"|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['namespace']} | {r['pods']} | {r['mem_mib_median']} | {r['mem_mib_max']} | {r['cpu_m_median']} |")
    print(f"| **all pods** | | **{result['pods_total_mem_mib_median']}** | | |")
    for n in node_rows:
        print(f"| node container `{n['node']}` | | {n['mem_mib_median']} | | |")
    print(f"| **kind nodes total (docker stats)** | | **{result['nodes_total_mem_mib_median']}** | | |")
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
