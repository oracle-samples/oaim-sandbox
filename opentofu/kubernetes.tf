locals {
  adb_name = lower(format("%sdb", oci_database_autonomous_database.default_adb.db_name))

  helm_values = templatefile("templates/helm_values.yaml", {
    label                    = local.label_prefix
    server_repository        = local.server_repository
    client_repository        = local.client_repository
    oci_region               = var.region
    adb_ocid                 = oci_database_autonomous_database.default_adb.id
    adb_name                 = local.adb_name
    k8s_node_pool_gpu_deploy = var.k8s_node_pool_gpu_deploy
    lb_ip                    = oci_core_public_ip.service_lb[0].ip_address
  })

  k8s_manifest = templatefile("templates/k8s_manifest.yaml", {
    label            = local.label_prefix
    compartment_ocid = local.compartment_ocid
    lb_subnet_ocid   = module.network.public_subnet_ocid
    lb_ip_ocid       = oci_core_public_ip.service_lb[0].id
    lb_nsgs          = format("%s, %s", oci_core_network_security_group.service_lb_app_client[0].id, oci_core_network_security_group.service_lb_app_server[0].id)
    adb_name         = local.adb_name
    adb_password     = oci_database_autonomous_database.default_adb.admin_password
    adb_service      = format("%s_TP", oci_database_autonomous_database.default_adb.db_name)
  })
}

resource "local_sensitive_file" "helm_values" {
  content         = local.helm_values
  filename        = "${path.root}/examples/${local.label_prefix}-values.yaml"
  file_permission = 0600
}

resource "local_sensitive_file" "k8s_manifest" {
  content         = local.k8s_manifest
  filename        = "${path.root}/examples/${local.label_prefix}-manifest.yaml"
  file_permission = 0600
}