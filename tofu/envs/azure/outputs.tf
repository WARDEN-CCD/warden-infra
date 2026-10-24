output "cluster_name" {
  value = module.aks.name
}

output "resource_group" {
  value = azurerm_resource_group.warden.name
}

output "kube_config_raw" {
  value     = module.aks.kube_config_raw
  sensitive = true
}

output "ci_client_id" {
  value = var.create_ci_identity ? module.ci_identity[0].client_id : null
}
