output "name" {
  value = azurerm_kubernetes_cluster.this.name
}

output "id" {
  value = azurerm_kubernetes_cluster.this.id
}

output "oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.this.oidc_issuer_url
}

output "kubelet_identity_object_id" {
  value       = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
  description = "Managed identity used by AKS nodes; granted only the Crossplane PostgreSQL role."
}
