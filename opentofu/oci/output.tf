# Copyright © 2023, 2024, Oracle and/or its affiliates.
# All rights reserved. The Universal Permissive License (UPL), Version 1.0 as shown at http://oss.oracle.com/licenses/upl

output "kubeconfig_cmd" {
  description = "Command to generate kubeconfig file"
  value = format(
    "oci ce cluster create-kubeconfig --cluster-id %s --region %s --token-version 2.0.0 --kube-endpoint %s --file $HOME/.kube/config",
    oci_containerengine_cluster.default_cluster.id,
    var.region,
    oci_containerengine_cluster.default_cluster.endpoint_config[0].is_public_ip_enabled ? "PUBLIC_ENDPOINT" : "PRIVATE_ENDPOINT"
  )
}

//ADB
output "adb_name" {
  description = "Autonomous Database Name"
  value       = var.byo_db ? var.byo_db_type == "ADB-S" ? data.oci_database_autonomous_database.byo_db[0].db_name : null : oci_database_autonomous_database.default_adb[0].db_name
}

output "adb_ip" {
  description = "Autonomous Database IP Address"
  value       = var.byo_db ? var.byo_db_type == "ADB-S" ? data.oci_database_autonomous_database.byo_db[0].private_endpoint_ip : null : var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? oci_database_autonomous_database.default_adb[0].private_endpoint_ip : "Secured Access"
}