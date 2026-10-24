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

variable "tags" {
  type    = map(string)
  default = {}
}
