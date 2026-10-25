"""Create bootstrap-only secrets that must never live in Git (hub DESIGN §14, CLAUDE.md rule 8).

  python scripts/bootstrap_secrets.py <cluster-name>

- Namespace `monitoring`, labelled warden.dev/monitored=true.
- Secret monitoring/grafana-admin with a random password. A copy goes to ~/.warden/grafana-admin-<cluster>
  so a human can log in; nothing is printed. Idempotent: an existing Secret is kept.
- Secret argocd/argocd-notifications-secret for the DORA ledger (ADR-019), when `warden setup-apps` has created
  the warden-ccd-deployments GitHub App: its private key (~/.warden/warden-ccd-deployments.pem) and the
  WARDEN_DEPLOYMENTS_APP_ID / _INSTALLATION_ID it wrote to ~/.warden/env. Skipped, not failed, without them.
Stdlib only. Secrets are sent on stdin, never as a command-line argument.
"""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

WARDEN = Path.home() / ".warden"


def kubectl(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", *args], input=stdin, capture_output=True, text=True)


def ensure_namespace(name: str) -> None:
    if kubectl("get", "namespace", name).returncode != 0:
        kubectl("create", "namespace", name)


def apply_secret(namespace: str, name: str, data: dict[str, str]) -> bool:
    manifest = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": namespace},
                "type": "Opaque", "stringData": data}
    result = kubectl("apply", "-f", "-", stdin=json.dumps(manifest))
    if result.returncode != 0:
        print(f"bootstrap_secrets: failed to create {namespace}/{name}: {result.stderr.strip()}")
    return result.returncode == 0


def grafana_admin(cluster: str) -> bool:
    ensure_namespace("monitoring")
    kubectl("label", "namespace", "monitoring", "warden.dev/monitored=true", "--overwrite")
    if kubectl("-n", "monitoring", "get", "secret", "grafana-admin").returncode == 0:
        print("bootstrap_secrets: monitoring/grafana-admin exists, kept")
        return True
    password = secrets.token_urlsafe(24)
    if not apply_secret("monitoring", "grafana-admin", {"admin-user": "admin", "admin-password": password}):
        return False
    local = WARDEN / f"grafana-admin-{cluster}"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(password + "\n", encoding="utf-8")
    print(f"bootstrap_secrets: created monitoring/grafana-admin; password saved to {local}")
    return True


def warden_env() -> dict[str, str]:
    """~/.warden/env as written by `warden setup-apps`; the process environment wins (Task's dotenv loads it)."""
    values: dict[str, str] = {}
    env_file = WARDEN / "env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    values.update({k: v for k, v in os.environ.items() if k.startswith("WARDEN_")})
    return values


def notifications_secret() -> bool:
    key = WARDEN / "warden-ccd-deployments.pem"
    env = warden_env()
    app_id, installation_id = env.get("WARDEN_DEPLOYMENTS_APP_ID"), env.get("WARDEN_DEPLOYMENTS_INSTALLATION_ID")
    if not (key.exists() and app_id and installation_id):
        print("bootstrap_secrets: no deployments GitHub App yet (run `warden setup-apps`); DORA ledger stays off")
        return True
    ensure_namespace("argocd")
    ok = apply_secret("argocd", "argocd-notifications-secret", {
        "github-appID": app_id,
        "github-installationID": installation_id,
        "github-privateKey": key.read_text(encoding="utf-8"),
    })
    if ok:
        print(f"bootstrap_secrets: argocd/argocd-notifications-secret set for app {app_id}")
    return ok


def main() -> int:
    cluster = sys.argv[1] if len(sys.argv) > 1 else "local"
    ok = grafana_admin(cluster)
    ok = notifications_secret() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
