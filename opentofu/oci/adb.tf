# Copyright © 2023, 2024, Oracle and/or its affiliates.
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
  count   = var.byo_db ? 0 : 1
  length  = 2
  special = false
  numeric = false
}

resource "random_password" "adb_rest" {
  count            = var.byo_db ? 0 : 1
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
  count                                = var.byo_db ? 0 : 1
  admin_password                       = sensitive(format("%s%s", random_password.adb_char[0].result, random_password.adb_rest[0].result))
  autonomous_maintenance_schedule_type = "REGULAR"
  character_set                        = "AL32UTF8"
  compartment_id                       = local.compartment_ocid
  compute_count                        = var.adb_compute_model == "ECPU" ? var.adb_ecpu_core_count : var.adb_ocpu_core_count
  compute_model                        = var.adb_compute_model
  data_storage_size_in_gb              = var.adb_compute_model == "ECPU" ? var.adb_data_storage_size_in_gb : null
  data_storage_size_in_tbs             = var.adb_compute_model == "OCPU" ? var.adb_data_storage_size_in_tbs : null
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

// Buckets
resource "oci_objectstorage_bucket" "adb" {
  count          = var.byo_db ? 0 : var.adb_create_bucket ? 1 : 0
  compartment_id = local.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.objectstorage_namespace.namespace
  name           = local.adb_bucket_name
  access_type    = "NoPublicAccess"
  auto_tiering   = "Disabled"
}

resource "oci_identity_dynamic_group" "adb_dynamic_group" {
  count          = var.byo_db ? 0 : var.adb_create_bucket ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = format("%s-adb-dyngrp", local.label_prefix)
  description    = format("%s Dynamic Group - ADB", local.label_prefix)
  matching_rule  = format("resource.id='%s'", oci_database_autonomous_database.default_adb[0].id)
  provider       = oci.home_region
}

resource "oci_identity_policy" "adb_policies" {
  count          = var.byo_db ? 0 : var.adb_create_bucket ? 1 : 0
  compartment_id = local.compartment_ocid
  name           = format("%s-adb-policy", local.label_prefix)
  description    = format("%s Policy - ADB", local.label_prefix)
  statements = [
    format("allow dynamic-group %s to manage buckets in compartment id %s where target.bucket.name='%s'", oci_identity_dynamic_group.adb_dynamic_group[0].name, local.compartment_ocid, oci_objectstorage_bucket.adb[0].name),
    format("allow dynamic-group %s to manage objects in compartment id %s where target.bucket.name='%s'", oci_identity_dynamic_group.adb_dynamic_group[0].name, local.compartment_ocid, oci_objectstorage_bucket.adb[0].name)
  ]
  provider = oci.home_region
}

resource "oci_bastion_bastion" "adb_bastion" {
  count                        = var.byo_db ? 0 : local.adb_enable_bastion ? 1 : 0
  compartment_id               = local.compartment_ocid
  bastion_type                 = "STANDARD"
  target_subnet_id             = module.network.private_subnet_ocid
  client_cidr_block_allow_list = local.adb_bastion_cidrs
  name                         = format("%sBastionService-ADB", local.label_prefix)
  dns_proxy_status             = "ENABLED"
  max_session_ttl_in_seconds   = 10800
}