"""Create the out-of-band service principal used by Crossplane's PostgreSQL provider."""

from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path

WARDEN = Path.home() / ".warden"
ENV_FILE = WARDEN / "env"


def run(*args: str) -> dict:
    result = subprocess.run(["az", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Azure CLI command failed")
    return json.loads(result.stdout or "{}")


def main() -> int:
    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                existing[key.strip()] = value.strip()

    needed = ("WARDEN_CROSSPLANE_CLIENT_ID", "WARDEN_CROSSPLANE_CLIENT_SECRET_B64",
              "WARDEN_CROSSPLANE_TENANT_ID", "TF_VAR_crossplane_object_id")
    if all(existing.get(key) for key in needed):
        print("bootstrap_crossplane_identity: credentials already exist in ~/.warden/env; kept")
        return 0

    account = run("account", "show", "--output", "json")
    subscription_id = existing.get("TF_VAR_subscription_id", account["id"])
    app = run("ad", "sp", "create-for-rbac", "--name", "warden-crossplane-postgresql",
              "--skip-assignment", "--years", "1", "--output", "json")
    if not all(app.get(key) for key in ("appId", "password", "tenant")):
        raise RuntimeError("Azure CLI did not return the service-principal credentials")
    principal = run("ad", "sp", "show", "--id", app["appId"], "--output", "json")
    values = {
        "WARDEN_CROSSPLANE_CLIENT_ID": app["appId"],
        "WARDEN_CROSSPLANE_CLIENT_SECRET_B64": base64.urlsafe_b64encode(app["password"].encode()).decode(),
        "WARDEN_CROSSPLANE_TENANT_ID": app["tenant"],
        "TF_VAR_crossplane_object_id": principal["id"],
        "TF_VAR_subscription_id": subscription_id,
    }
    existing.update(values)
    WARDEN.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(f"{key}={value}" for key, value in existing.items()) + "\n",
                        encoding="utf-8")
    if os.name != "nt":
        ENV_FILE.chmod(0o600)
    print("bootstrap_crossplane_identity: created PostgreSQL provider identity; credentials saved outside Git")
    print(f"bootstrap_crossplane_identity: object ID {principal['id']}; no Azure role has been assigned yet")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError) as exc:
        raise SystemExit(f"bootstrap_crossplane_identity: {exc}")
