output "cluster_name" {
  value = module.aks.name
}

output "resource_group" {
  value = azurerm_resource_group.warden.name
}

# Local accounts are disabled, so there is no static kubeconfig to output. Operators run
#   az aks get-credentials -g <resource_group> -n <cluster_name> && kubelogin convert-kubeconfig -l azurecli

output "ci_client_id" {
  value = var.create_ci_identity ? module.ci_identity[0].client_id : null
}
