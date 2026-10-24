# Ephemeral AKS cluster for Warden (ADR-003, ADR-004). Free tier control plane; B-series nodes sized to the
# Azure for Students quota (4 B-series vCPU). Azure CNI overlay + Cilium so NetworkPolicies are enforced.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.10.0"
    }
  }
}

resource "azurerm_kubernetes_cluster" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.name
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Free"

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # Entra ID only: no static admin certificate exists, and Kubernetes authorization is Azure RBAC, so access is
  # a role assignment that disappears with the cluster. Operators connect with az + kubelogin.
  local_account_disabled = true
  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
    tenant_id          = var.tenant_id
  }

  # The API server answers only the operators' addresses (AKS adds the cluster's own egress IP). CI never
  # talks to the cluster (T09); Argo CD pulls from inside it.
  api_server_access_profile {
    authorized_ip_ranges = var.api_authorized_cidrs
  }

  default_node_pool {
    name                        = "system"
    vm_size                     = var.node_size
    node_count                  = var.node_count
    os_disk_size_gb             = 64
    temporary_name_for_rotation = "rotate"
  }

  # azurerm 5.x requires this block. Manual = no node auto-provisioning: the fixed pool above is the whole
  # cluster, so cost stays inside the 4 vCPU quota.
  node_provisioning_profile {
    mode = "Manual"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    network_policy      = "cilium"
    load_balancer_sku   = "standard"
  }

  tags = var.tags
}

resource "azurerm_role_assignment" "cluster_admin" {
  for_each             = toset(var.admin_object_ids)
  scope                = azurerm_kubernetes_cluster.this.id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = each.value
}
