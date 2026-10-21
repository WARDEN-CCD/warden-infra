# OpenTofu layout (weeks 4–6)

| Stack | Creates | State |
|-------|---------|-------|
| `bootstrap/` | Resource group `warden-tfstate`, storage account (TLS 1.2+, no public blob access), container `tfstate` | local, run once per subscription |
| `envs/azure/` | Resource group `warden`, AKS (Free tier, 1.37, 2 × B2ms, OIDC issuer + workload identity on), budget, GitHub OIDC federated credential | azurerm backend, encrypted |

Planned module interfaces:

- `modules/aks`: `name`, `location`, `kubernetes_version`, `node_size`, `node_count`, `tags` → `kube_config_raw`
  (sensitive, consumed only by the local bootstrap task), `oidc_issuer_url`.
- `modules/budget`: `amount_usd`, `contact_emails`, thresholds `[25, 50, 75]`.
- `modules/github-oidc`: `github_org`, `repo`, `environment` → client ID for `azure/login` with OIDC.

Open items for spike S3: confirm B2ms availability in `indiasouthcentral`; confirm OpenTofu state-encryption key
provider choice (passphrase from `~/.warden/` vs a cloud KMS); measure `tofu apply` time for AKS.
