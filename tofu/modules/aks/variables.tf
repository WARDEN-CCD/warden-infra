variable "name" {
  type        = string
  description = "Cluster name, also the DNS prefix."
}

variable "location" {
  type        = string
  description = "Azure region; must be allowed by the subscription policy (hub workspace.yaml azure.allowedRegions)."
}

variable "resource_group_name" {
  type = string
}

variable "kubernetes_version" {
  type    = string
  default = "1.37"
}

variable "node_size" {
  type    = string
  default = "Standard_B2ms"
}

variable "node_count" {
  type    = number
  default = 2

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 2
    error_message = "The student subscription's B-series quota is 4 vCPU: at most 2 x B2ms."
  }
}

variable "tenant_id" {
  type        = string
  description = "Entra tenant for the cluster's Azure RBAC integration."
}

variable "admin_object_ids" {
  type        = list(string)
  description = "Entra object IDs given Azure Kubernetes Service RBAC Cluster Admin on this cluster only."

  validation {
    condition     = length(var.admin_object_ids) > 0
    error_message = "With local accounts disabled, at least one admin is needed or nobody can reach the cluster."
  }
}

variable "api_authorized_cidrs" {
  type        = list(string)
  description = "Addresses allowed to reach the API server (operators' public IPs as /32)."

  validation {
    condition     = length(var.api_authorized_cidrs) > 0 && !contains(var.api_authorized_cidrs, "0.0.0.0/0")
    error_message = "List the operators' addresses; an empty list or 0.0.0.0/0 leaves the API server open."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
