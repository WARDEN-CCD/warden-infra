# Crossplane APIs (ADR-016)

Crossplane v2.4 installs from `warden-gitops/platform/crossplane/`; this folder holds the APIs it serves.

| Path | Content |
|------|---------|
| `base/xrds/database.yaml` | `Database` (`platform.warden.dev/v1alpha1`, namespaced) — the shared developer contract |
| `base/functions/` | `function-go-templating` v0.13.1, `function-auto-ready` v0.7.2 |
| `overlays/local/` | `database-default` composes a CloudNativePG `Cluster` and `<name>-conn` Secret |
| `overlays/azure/` | `database-default` composes a Flexible Server, database, egress firewall rule and `<name>-conn` Secret |
| `overlays/azure/providers.yaml` | Pinned Azure provider packages; the ClusterProviderConfig is bootstrap-generated with AKS managed identity |

Crossplane needs RBAC to manage CNPG `Cluster` objects (v2 composes arbitrary resources); the local overlay supplies
that ClusterRole. The Azure overlay supplies a separate role for the Flexible Server, database and firewall-rule
managed resources. Azure Flexible Server firewall access is restricted to the AKS egress IPv4 address supplied in
`spec.network.allowedSourceIp`; kind ignores this optional field. For Azure, retrieve the current address after AKS
creation with `az aks show -g warden -n warden --query 'networkProfile.loadBalancerProfile.effectiveOutboundIPs[].id' -o tsv`
and `az network public-ip show --ids <id> --query ipAddress -o tsv`. Reuse the same `Database` manifest after setting
that value; the field has no effect on the local backend. The Azure bootstrap creates a cluster-scoped
`ClusterProviderConfig` from `azure.m.upbound.io/v1beta1`, selecting the AKS kubelet user-assigned identity by its
client ID. This follows the pinned provider's [v2.8.0 managed-identity configuration](https://github.com/crossplane-contrib/provider-upjet-azure/blob/v2.8.0/AUTHENTICATION.md).
Each server name includes a suffix derived from the `Database` resource UID because Azure requires globally unique
Flexible Server names.
