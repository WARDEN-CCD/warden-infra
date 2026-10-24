# One-time per subscription: the storage that holds envs/azure's (encrypted) state. Kept in local state on the
# operator's machine; it contains no secrets (access is Entra ID only, shared keys are disabled).

terraform {
  required_version = ">= 1.13.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.10.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.9.1"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

variable "subscription_id" {
  type = string
}

variable "location" {
  type    = string
  default = "indiasouthcentral"
}

data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "state" {
  name     = "warden-tfstate"
  location = var.location
}

resource "azurerm_storage_account" "state" {
  name                            = "wardenstate${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.state.name
  location                        = azurerm_resource_group.state.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true

  blob_properties {
    versioning_enabled = true
  }
}

resource "azurerm_role_assignment" "operator_blob" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_storage_container" "state" {
  name               = "tfstate"
  storage_account_id = azurerm_storage_account.state.id
  depends_on         = [azurerm_role_assignment.operator_blob]
}

output "backend_config" {
  description = "Pass to `tofu init -backend-config=...` in envs/azure (task up:azure writes ~/.warden/backend.hcl)."
  value = {
    resource_group_name  = azurerm_resource_group.state.name
    storage_account_name = azurerm_storage_account.state.name
    container_name       = azurerm_storage_container.state.name
    key                  = "warden-azure.tfstate"
    use_azuread_auth     = true
  }
}
