# Copyright © 2023, 2024, Oracle and/or its affiliates.
# All rights reserved. The Universal Permissive License (UPL), Version 1.0 as shown at http://oss.oracle.com/licenses/upl

// oke API Endpoint
resource "oci_core_network_security_group" "oke_api_endpoint" {
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-oke-api-endpoint", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}

// oke Worker Node Pool
resource "oci_core_network_security_group" "oke_workers" {
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-oke-workers", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}

// Load Balancer
resource "oci_core_network_security_group" "service_lb" {
  count          = var.service_lb_is_public ? 1 : 0
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-service-lb", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}

resource "oci_core_network_security_group" "adb" {
  count          = var.adb_networking == "PRIVATE_ENDPOINT_ACCESS" ? 1 : 0
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-adb", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}