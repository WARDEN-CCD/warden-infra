"""Create bootstrap-only secrets that must never live in Git (hub DESIGN §14, CLAUDE.md rule 8).

  python scripts/bootstrap_secrets.py <cluster-name>

- Namespace `monitoring`, labelled warden.dev/monitored=true.
- Secret monitoring/grafana-admin with a random password. A copy goes to ~/.warden/grafana-admin-<cluster>
  so a human can log in; nothing is printed. Idempotent: an existing Secret is kept.
Stdlib only. The Secret is sent on stdin, never as a command-line argument.
"""

import json
import secrets
import subprocess
import sys
from pathlib import Path


def kubectl(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", *args], input=stdin, capture_output=True, text=True)


def main() -> int:
    cluster = sys.argv[1] if len(sys.argv) > 1 else "local"

    if kubectl("get", "namespace", "monitoring").returncode != 0:
        kubectl("create", "namespace", "monitoring")
    kubectl("label", "namespace", "monitoring", "warden.dev/monitored=true", "--overwrite")

    if kubectl("-n", "monitoring", "get", "secret", "grafana-admin").returncode == 0:
        print("bootstrap_secrets: monitoring/grafana-admin exists, kept")
        return 0

    password = secrets.token_urlsafe(24)
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "grafana-admin", "namespace": "monitoring"},
        "type": "Opaque",
        "stringData": {"admin-user": "admin", "admin-password": password},
    }
    result = kubectl("apply", "-f", "-", stdin=json.dumps(manifest))
    if result.returncode != 0:
        print(f"bootstrap_secrets: failed to create grafana-admin: {result.stderr.strip()}")
        return 1

    local = Path.home() / ".warden" / f"grafana-admin-{cluster}"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(password + "\n", encoding="utf-8")
    print(f"bootstrap_secrets: created monitoring/grafana-admin; password saved to {local}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
