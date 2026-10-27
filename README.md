# warden-infra

Everything that creates a Warden environment, plus the platform's self-service infrastructure APIs.
Design: hub `DESIGN.md` §10, §13–15; decisions ADR-003, 004, 005, 016.

```
kind/warden.yaml          local cluster (Kubernetes 1.37, node image pinned by digest)
tofu/
  bootstrap/              one-time: resource group + storage account/container for encrypted tofu state
  modules/aks/            AKS Free tier, 1 pool of 2 × Standard_B2ms, OIDC issuer enabled
  modules/budget/         subscription budget US$100 with 25/50/75 % alerts
  modules/github-oidc/    Entra app + federated credential for this repo's `azure` environment (no secrets)
  envs/azure/             composition of the modules for indiasouthcentral
crossplane/
  xrds/                   Database XRD (developer API)
  compositions/           database-cnpg (pipeline mode, function-go-templating); database-azure is designed, not written
  functions/ providers/   Function and Provider packages, pinned
scripts/ledger.py         appends each up/rebuild to the hub's evidence/rebuilds/rebuild-ledger.csv
Taskfile.yml              up/down/rebuild for local and azure
```

## Usage

```bash
task up:local        # kind + Argo CD + root app; ledger row appended
task down:local
task rebuild:local   # timed destroy + create (evaluation E6)
task up:azure        # about 20 min from an empty subscription; ALWAYS follow with task down:azure
task down:azure
```

## Azure operations notes

- State lives in the `warden-tfstate` storage account, encrypted by OpenTofu with `TF_VAR_state_passphrase` from
  `~/.warden/env`. If that passphrase changes, the stored state cannot be read. Keep a copy outside the file. On
  2026-10-27 the key in `~/.warden/backend.hcl` was moved to `warden-azure-2.tfstate` for this reason (the old state
  described an environment that was already destroyed); after changing `key`, run `tofu init -reconfigure` once in
  `tofu/envs/azure`.
- `up:azure` runs `az aks get-credentials`, which makes AKS the current kubectl context. If something else is using the
  kind cluster, set `KUBECONFIG` to a separate file first (the hub's `scripts/experiments/azure_rebuilds.py` has a
  `--kubeconfig` option).
- After any Azure work: `az group list --query "[].name" -o tsv` should show only `NetworkWatcherRG` and
  `warden-tfstate`.

## Rules

- Nothing outside this repo and `warden-gitops` may be needed to rebuild an environment, except the GitHub App
  keys in `~/.warden/`.
- Azure auth from CI is OIDC only. Never create a client secret.
- Allowed regions on the student subscriptions: `indiasouthcentral` (default), `koreacentral`, `eastasia`,
  `uaenorth`, `indonesiacentral`. B-series quota 4 vCPU.
- AKS clusters are ephemeral. The reaper workflow destroys anything older than 8 hours.
