# Copyright (c) 2024, 2025, Oracle and/or its affiliates.
# All rights reserved. The Universal Permissive License (UPL), Version 1.0 as shown at http://oss.oracle.com/licenses/upl

// API Endpoint
resource "oci_core_network_security_group" "k8s_api_endpoint" {
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-k8s-api-endpoint", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}

// Worker Node Pool
resource "oci_core_network_security_group" "k8s_workers" {
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-k8s-workers", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}

// Load Balancer
resource "oci_core_network_security_group" "service_lb_http" {
  count          = var.service_lb_is_public ? 1 : 0
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-service-lb-http", local.label_prefix)
  lifecycle {
    ignore_changes = [defined_tags, freeform_tags]
  }
}

resource "oci_core_network_security_group" "service_lb_api" {
  count          = var.service_lb_is_public ? 1 : 0
  compartment_id = local.compartment_ocid
  vcn_id         = module.network.vcn_ocid
  display_name   = format("%s-service-lb-api", local.label_prefix)
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