# CLAUDE.md — warden-infra

OpenTofu, kind, Crossplane APIs. Workspace rules: `../CLAUDE.md` (hub).

- Use `tofu`, not `terraform` (ADR-005). Pin provider versions; commit `.terraform.lock.hcl`; never commit state.
- State: azurerm backend with OIDC auth and OpenTofu state encryption. No secrets in `.tf` or `.tfvars`.
- Respect the student subscription: allowed regions only (see README), ≤ 4 B-series vCPU, AKS Free tier,
  budget module always included. Never leave an AKS cluster running.
- The kind node image must equal the hub's `versions.yaml` `kubernetes.kindNodeImage`.
- Crossplane v2 only: `apiextensions.crossplane.io/v2` XRDs, `scope: Namespaced`, no claims, pipeline-mode
  compositions with functions, compose a `<name>-conn` Secret for connection details.
- Every environment operation goes through the Taskfile so it lands in the rebuild ledger.
- Before claiming a tofu change works: `tofu fmt -check`, `tofu validate`, and a `tofu plan` output.
