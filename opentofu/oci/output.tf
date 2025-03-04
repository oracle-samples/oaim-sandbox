# Copyright (c) 2024-2025, Oracle and/or its affiliates.
# All rights reserved. The Universal Permissive License (UPL), Version 1.0 as shown at http://oss.oracle.com/licenses/upl

output "lb_reserved_ip" {
  value = oci_core_public_ip.service_lb[0].ip_address
}

output "lb_nsg_ocid" {
  value = format("%s, %s", oci_core_network_security_group.service_lb_http[0].id, oci_core_network_security_group.service_lb_api[0].id)
}

output "adb_ocid" {
  description = "Autonomous Database OCID"
  value       = oci_database_autonomous_database.default_adb.id
}

output "adb_password" {
  description = "Autonomous Database ADMIN Password"
  value       = oci_database_autonomous_database.default_adb.admin_password
  sensitive   = true
}

output "adb_service" {
  description = "Autonomous Database Service Name"
  value       = format("%s_TP", oci_database_autonomous_database.default_adb.db_name)
}

output "oci_region" {
  description = "OCI Region"
  value       = var.region
}

output "sandbox_repository" {
  value = lower(format("%s.ocir.io/%s/%s", local.image_region, data.oci_objectstorage_namespace.objectstorage_namespace.namespace, oci_artifacts_container_repository.sandbox_repository.display_name))
}

output "server_repository" {
  value = lower(format("%s.ocir.io/%s/%s", local.image_region, data.oci_objectstorage_namespace.objectstorage_namespace.namespace, oci_artifacts_container_repository.server_repository.display_name))
}

output "kubeconfig_cmd" {
  description = "Command to generate kubeconfig file"
  value = format(
    "oci ce cluster create-kubeconfig --cluster-id %s --region %s --token-version 2.0.0 --kube-endpoint %s --file $HOME/.kube/config",
    oci_containerengine_cluster.default_cluster.id,
    var.region,
    oci_containerengine_cluster.default_cluster.endpoint_config[0].is_public_ip_enabled ? "PUBLIC_ENDPOINT" : "PRIVATE_ENDPOINT"
  )
}