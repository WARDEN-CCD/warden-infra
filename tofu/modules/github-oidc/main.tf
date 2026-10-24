# GitHub Actions -> Azure without secrets (ADR-005): an Entra application whose only credential is a federated
# identity bound to one repo's GitHub environment, with Contributor on the Warden resource group only.

terraform {
  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "3.10.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.10.0"
    }
  }
}

variable "github_org" {
  type = string
}

variable "repo" {
  type = string
}

variable "environment" {
  type        = string
  description = "GitHub environment allowed to assume the identity (protected by a required reviewer)."
}

variable "scope_resource_group_id" {
  type = string
}

resource "azuread_application" "ci" {
  display_name = "warden-${var.repo}-${var.environment}"
}

resource "azuread_service_principal" "ci" {
  client_id = azuread_application.ci.client_id
}

resource "azuread_application_federated_identity_credential" "github" {
  application_id = azuread_application.ci.id
  display_name   = "github-${var.repo}-${var.environment}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_org}/${var.repo}:environment:${var.environment}"
}

resource "azurerm_role_assignment" "contributor" {
  scope                = var.scope_resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.ci.object_id
}

output "client_id" {
  value = azuread_application.ci.client_id
}
