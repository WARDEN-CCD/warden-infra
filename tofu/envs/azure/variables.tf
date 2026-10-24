variable "state_passphrase" {
  type        = string
  sensitive   = true
  description = "State/plan encryption passphrase (TF_VAR_state_passphrase from ~/.warden/env)."

  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "Use a passphrase of at least 16 characters."
  }
}

variable "subscription_id" {
  type = string
}

variable "location" {
  type    = string
  default = "indiasouthcentral"

  validation {
    condition     = contains(["indiasouthcentral", "koreacentral", "eastasia", "uaenorth", "indonesiacentral"], var.location)
    error_message = "The Azure for Students policy only allows the regions in hub workspace.yaml azure.allowedRegions."
  }
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
}

variable "budget_usd" {
  type    = number
  default = 100
}

variable "budget_start_date" {
  type        = string
  description = "First day of the current month, RFC 3339."
}

variable "contact_emails" {
  type        = list(string)
  description = "Budget alert recipients."
}

variable "create_ci_identity" {
  type        = bool
  default     = false
  description = "Create the Entra app + federated credential for warden-infra's `azure` environment."
}
