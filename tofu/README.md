# OpenTofu layout

| Stack | Creates | State |
|-------|---------|-------|
| `bootstrap/` | Resource group `warden-tfstate`, storage account (TLS 1.2+, no public blob access), container `tfstate` | local, run once per subscription |
| `envs/azure/` | Resource group `warden`, AKS (Free tier, 1.37, 2 × B2ms, OIDC issuer + workload identity on), budget, GitHub OIDC federated credential | azurerm backend, encrypted |

Module interfaces:

- `modules/aks`: `name`, `location`, `kubernetes_version`, `node_size`, `node_count`, `tags` → `kube_config_raw`
  (sensitive, consumed only by the local bootstrap task), `oidc_issuer_url`.
- `modules/budget`: `amount_usd`, `contact_emails`, thresholds `[25, 50, 75]`.
- `modules/github-oidc`: `github_org`, `repo`, `environment` → client ID for `azure/login` with OIDC.

Decided and measured (spike S3, first run 2026-10-26): B2ms is available in `indiasouthcentral`; the state encryption key
comes from a passphrase in `~/.warden/env`; AKS creation took 333 s and `task up:azure` as a whole 1203 s. See the hub's
`evidence/azure/`.
