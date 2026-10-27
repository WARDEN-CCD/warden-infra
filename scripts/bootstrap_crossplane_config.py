"""Save Azure account metadata and apply the Crossplane managed-identity ProviderConfig."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WARDEN = Path.home() / ".warden"
ENV_FILE = WARDEN / "env"


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    return values


def azure_cli() -> str:
    if os.name == "nt":
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Get-Command az -CommandType Application | Select-Object -First 1 -ExpandProperty Source"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    return "az"


def run_az(*args: str) -> dict:
    command = [azure_cli(), *args]
    if os.name == "nt":
        result = subprocess.run(subprocess.list2cmdline(command), shell=True, capture_output=True, text=True)
    else:
        result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Azure CLI command failed")
    return json.loads(result.stdout or "{}")


def kubectl(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", *args], input=stdin, capture_output=True, text=True)


def save_account() -> dict[str, str]:
    account = run_az("account", "show", "--output", "json")
    values = read_env()
    configured_subscription = os.environ.get("TF_VAR_subscription_id") or values.get("TF_VAR_subscription_id")
    if configured_subscription and configured_subscription.lower() != account["id"].lower():
        raise RuntimeError("active Azure subscription does not match TF_VAR_subscription_id in ~/.warden/env")
    values["TF_VAR_subscription_id"] = account["id"]
    values["TF_VAR_tenant_id"] = account["tenantId"]
    WARDEN.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
                        encoding="utf-8")
    print("bootstrap_crossplane_config: saved non-secret Azure subscription and tenant IDs in ~/.warden/env")
    return values


def apply_provider_config() -> None:
    values = read_env()
    subscription, tenant = values.get("TF_VAR_subscription_id"), values.get("TF_VAR_tenant_id")
    if not subscription or not tenant:
        raise RuntimeError("Azure subscription or tenant ID missing; run task bootstrap:crossplane-config first")
    aks = run_az("aks", "show", "--resource-group", "warden", "--name", "warden", "--output", "json")
    try:
        kubelet_client_id = aks["identityProfile"]["kubeletidentity"]["clientId"]
    except KeyError as exc:
        raise RuntimeError("AKS kubelet managed identity client ID is unavailable") from exc
    for _ in range(60):
        crd = kubectl("get", "crd", "clusterproviderconfigs.azure.m.upbound.io")
        if crd.returncode == 0:
            break
        time.sleep(10)
    else:
        raise RuntimeError("Azure ClusterProviderConfig CRD did not become available after provider installation")
    provider_config = {
        "apiVersion": "azure.m.upbound.io/v1beta1",
        "kind": "ClusterProviderConfig",
        "metadata": {"name": "default"},
        "spec": {
            "credentials": {"source": "UserAssignedManagedIdentity"},
            "clientID": kubelet_client_id,
            "subscriptionID": subscription,
            "tenantID": tenant,
        },
    }
    result = kubectl("apply", "-f", "-", stdin=json.dumps(provider_config))
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ProviderConfig apply failed")
    print("bootstrap_crossplane_config: applied ClusterProviderConfig using the AKS kubelet managed identity")


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "env"
    if action == "env":
        save_account()
    elif action == "apply":
        apply_provider_config()
    else:
        raise RuntimeError("usage: bootstrap_crossplane_config.py [env|apply]")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, RuntimeError) as exc:
        raise SystemExit(f"bootstrap_crossplane_config: {exc}")
