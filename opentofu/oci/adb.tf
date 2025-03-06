# Copyright (c) 2024-2025, Oracle and/or its affiliates.
# All rights reserved. The Universal Permissive License (UPL), Version 1.0 as shown at http://oss.oracle.com/licenses/upl

locals {
  adb_enable_bastion         = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? true : false
  adb_bastion_cidrs          = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? split(",", replace(var.adb_bastion_cidrs, "/\\s+/", "")) : []
  adb_whitelist_cidrs        = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? null : concat(split(",", replace(var.adb_whitelist_cidrs, "/\\s+/", "")), [module.network.vcn_ocid])
  adb_nsg                    = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? [oci_core_network_security_group.adb[0].id] : []
  adb_subnet_id              = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? module.network.private_subnet_ocid : null
  adb_private_endpoint_label = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? local.label_prefix : null
}

resource "random_password" "adb_char" {
  length  = 2
  special = false
  numeric = false
}

resource "random_password" "adb_rest" {
  length           = 14
  min_numeric      = 2
  min_lower        = 2
  min_upper        = 2
  min_special      = 2
  override_special = "!$%^*-_"
  keepers = {
    uuid = "uuid()"
  }
}

resource "oci_database_autonomous_database" "default_adb" {
  admin_password                       = sensitive(format("%s%s", random_password.adb_char.result, random_password.adb_rest.result))
  autonomous_maintenance_schedule_type = "REGULAR"
  character_set                        = "AL32UTF8"
  compartment_id                       = local.compartment_ocid
  compute_count                        = var.adb_ecpu_core_count
  compute_model                        = "ECPU"
  data_storage_size_in_gb              = var.adb_data_storage_size_in_gb
  database_edition                     = var.adb_license_model == "BRING_YOUR_OWN_LICENSE" ? var.adb_edition : null
  db_name                              = format("%sDB", upper(local.label_prefix))
  db_version                           = var.adb_version
  db_workload                          = "OLTP"
  display_name                         = format("%sDB", upper(local.label_prefix))
  is_free_tier                         = false
  is_auto_scaling_enabled              = var.adb_is_cpu_auto_scaling_enabled
  is_auto_scaling_for_storage_enabled  = var.adb_is_storage_auto_scaling_enabled
  is_dedicated                         = false
  license_model                        = var.adb_license_model
  is_mtls_connection_required          = true //Always true, otherwise can't switch between Private Endpoint/Secure Access
  nsg_ids                              = local.adb_nsg
  whitelisted_ips                      = local.adb_whitelist_cidrs
  private_endpoint_label               = local.adb_private_endpoint_label
  subnet_id                            = local.adb_subnet_id
  lifecycle {
    // cannot change from PRIVATE_ENDPOINT_ACCESS to SECURE_ACCESS
    ignore_changes = [whitelisted_ips, private_endpoint_label, subnet_id]
  }
}