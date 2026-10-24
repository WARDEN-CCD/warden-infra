# Warden's Azure environment (ADR-003/004/005): resource group, ephemeral AKS, budget guardrail, and optionally
# the GitHub OIDC identity for CI. State lives in the bootstrap storage account, encrypted client-side.

terraform {
  required_version = ">= 1.13.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.10.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "3.10.0"
    }
  }

  # Configured at init time: tofu init -backend-config=$HOME/.warden/backend.hcl (output of tofu/bootstrap).
  backend "azurerm" {}

  # OpenTofu native state encryption (ADR-005). The passphrase comes from TF_VAR_state_passphrase,
  # kept in ~/.warden/env, never in Git.
  encryption {
    key_provider "pbkdf2" "passphrase" {
      passphrase = var.state_passphrase
    }
    method "aes_gcm" "default" {
      keys = key_provider.pbkdf2.passphrase
    }
    state {
      method   = method.aes_gcm.default
      enforced = true
    }
    plan {
      method   = method.aes_gcm.default
      enforced = true
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

provider "azuread" {}

resource "azurerm_resource_group" "warden" {
  name     = "warden"
  location = var.location
  tags     = local.tags
}

locals {
  tags = { project = "warden", ephemeral = "true", managed-by = "opentofu" }
}

module "aks" {
  source              = "../../modules/aks"
  name                = "warden"
  location            = azurerm_resource_group.warden.location
  resource_group_name = azurerm_resource_group.warden.name
  kubernetes_version  = var.kubernetes_version
  node_size           = var.node_size
  node_count          = var.node_count
  tags                = local.tags
}

module "budget" {
  source          = "../../modules/budget"
  subscription_id = var.subscription_id
  amount_usd      = var.budget_usd
  start_date      = var.budget_start_date
  contact_emails  = var.contact_emails
}

module "ci_identity" {
  count                   = var.create_ci_identity ? 1 : 0
  source                  = "../../modules/github-oidc"
  github_org              = "WARDEN-CCD"
  repo                    = "warden-infra"
  environment             = "azure"
  scope_resource_group_id = azurerm_resource_group.warden.id
}
