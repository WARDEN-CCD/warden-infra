# Crossplane APIs (ADR-016)

Crossplane v2.4 installs from `warden-gitops/platform/crossplane/`; this folder holds the APIs it serves.

| Path | Content |
|------|---------|
| `xrds/database.yaml` | `Database` (`platform.warden.dev/v1alpha1`, namespaced) — the developer contract |
| `compositions/database-cnpg.yaml` | composes a CloudNativePG `Cluster` + `<name>-conn` Secret (local default) |
| `compositions/database-azure.yaml` | composes `FlexibleServer`, `FlexibleServerDatabase`, firewall rule + `<name>-conn` Secret (azure default) |
| `functions/` | `function-go-templating` v0.13.1, `function-auto-ready` v0.7.2 (fully qualified package refs) |
| `providers/` | `provider-upjet-azure` (crossplane-contrib) PostgreSQL family member v2.8.0, `DeploymentRuntimeConfig` |

Crossplane needs RBAC to manage CNPG `Cluster` objects (v2 composes arbitrary resources) — add a ClusterRole
with the `rbac.crossplane.io/aggregate-to-crossplane: "true"` label.
