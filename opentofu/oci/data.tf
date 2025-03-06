# Copyright (c) 2024, 2025, Oracle and/or its affiliates.
# All rights reserved. The Universal Permissive License (UPL), Version 1.0 as shown at http://oss.oracle.com/licenses/upl

// oci_artifacts
data "oci_artifacts_container_repositories" "container_repositories" {
  compartment_id = local.compartment_ocid
  display_name   = lower(format("%s/*", local.label_prefix))
  depends_on = [
    oci_containerengine_cluster.default_cluster
  ]
}

// oci_containerengine
data "oci_containerengine_node_pool_option" "images" {
  node_pool_option_id = oci_containerengine_cluster.default_cluster.id
  compartment_id      = local.compartment_ocid
}

// oci_core
data "oci_core_services" "core_services" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

// oci_identity
data "oci_identity_availability_domains" "all" {
  compartment_id = var.tenancy_ocid
}

data "oci_identity_compartments" "all_compartments" {
  count                     = data.oci_identity_user.identity_user.name == null ? 1 : 0
  compartment_id            = var.tenancy_ocid
  access_level              = "ANY"
  compartment_id_in_subtree = true
}

data "oci_identity_regions" "identity_regions" {}

data "oci_identity_user" "identity_user" {
  user_id = local.user_ocid
}

data "oci_identity_domains" "all_domains" {
  for_each       = data.oci_identity_user.identity_user.name == null ? toset(concat(data.oci_identity_compartments.all_compartments[0].compartments[*].id, [var.tenancy_ocid])) : toset([])
  compartment_id = each.key
}

data "oci_identity_domains_user" "domain_user" {
  for_each = {
    for url in flatten([
      for compartment_id, compartment in data.oci_identity_domains.all_domains : [
        for domain in compartment.domains : domain.url
      ]
    ]) : url => url
  }
  idcs_endpoint = each.value
  user_id       = local.user_ocid
}

data "oci_identity_domain" "user_domain" {
  count     = data.oci_identity_user.identity_user.name == null ? 1 : 0
  domain_id = local.domain_user_details[0].domain_ocid
}

// oci_objectstorage
data "oci_objectstorage_namespace" "objectstorage_namespace" {
  compartment_id = local.compartment_ocid
}

// Look for where the GPU workers can be placed
data "oci_limits_limit_values" "gpu_ad_limits" {
  compartment_id = var.tenancy_ocid
  service_name   = "compute"
  scope_type     = "AD"
  name           = "gpu-a10-count"
}

# https://registry.terraform.io/providers/hashicorp/template/latest/docs/data-sources/cloudinit_config.html
data "cloudinit_config" "workers" {
  gzip          = true
  base64_encode = true

  # Expand root filesystem to fill available space on volume
  part {
    content_type = "text/cloud-config"
    content = jsonencode({
      # https://cloudinit.readthedocs.io/en/latest/reference/modules.html#growpart
      growpart = {
        mode                     = "auto"
        devices                  = ["/"]
        ignore_growroot_disabled = false
      }

      # https://cloudinit.readthedocs.io/en/latest/reference/modules.html#resizefs
      resize_rootfs = true

      # Resize logical LVM root volume when utility is present
      bootcmd = ["if [[ -f /usr/libexec/oci-growfs ]]; then /usr/libexec/oci-growfs -y; fi"]
    })
    filename   = "10-growpart.yml"
    merge_type = "list(append)+dict(no_replace,recurse_list)+str(append)"
  }

  # OKE startup initialization
  part {
    content_type = "text/x-shellscript"
    content      = file("${path.root}/templates/cloudinit-oke.sh")
    filename     = "50-oke.sh"
    merge_type   = "list(append)+dict(no_replace,recurse_list)+str(append)"
  }
}

data "oci_containerengine_node_pool" "default_node_pool_details" {
  node_pool_id = oci_containerengine_node_pool.default_node_pool_details.id
}
data "oci_containerengine_node_pool" "gpu_node_pool_details" {
  count        = var.k8s_node_pool_gpu_deploy ? 1 : 0
  node_pool_id = oci_containerengine_node_pool.gpu_node_pool_details[0].id
}