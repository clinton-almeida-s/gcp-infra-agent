import json


def generate(spec: dict) -> str:
    """
    Convert a parsed resource spec into Terraform HCL.
    """
    hcl_blocks = []

    for res in spec.get("resources", []):
        rtype = res.get("type")
        rname = res.get("name")
        props = res.get("properties", {})

        if rtype == "google_compute_vpc":
            block = f"""resource "google_compute_vpc" "{rname}" {{
  name                    = "{rname}"
  auto_create_subnetworks = {str(props.get('auto_create_subnetworks', False)).lower()}
}}"""
            hcl_blocks.append(block)

        elif rtype == "google_compute_subnet":
            cidr = props.get('ip_cidr_range')
            region = props.get('region', 'us-central1')
            vpc_ref = props.get('vpc', 'inferred')
            block = f"""resource "google_compute_subnet" "{rname}" {{
  name          = "{rname}"
  ip_cidr_range = "{cidr}"
  region        = "{region}"
  vpc_id        = google_compute_vpc.{vpc_ref}.id
}}"""
            hcl_blocks.append(block)

        elif rtype == "google_cloud_run_service":
            cpu = props.get('cpu', '1')
            memory = props.get('memory', '512Mi')
            ingress = props.get('ingress', 'ALL')
            block = f"""resource "google_cloud_run_service" "{rname}" {{
  name     = "{rname}"
  location = "us-central1"
  template {{
    spec {{
      containers {{
        image = "gcr.io/cloudrun/hello"
        resources {{
          limits = {{
            cpu    = "{cpu}"
            memory = "{memory}"
          }}
        }}
      }}
    }}
  }}
  metadata {{
    annotations = {{
      "run.googleapis.com/ingress" = "{ingress}"
    }}
  }}
}}"""
            hcl_blocks.append(block)

        elif rtype == "google_sql_database_instance":
            db_ver = props.get('database_version', 'POSTGRES_15')
            region = props.get('region', 'us-central1')
            tier = props.get('tier', 'db-f1-micro')
            block = f"""resource "google_sql_database_instance" "{rname}" {{
  name             = "{rname}"
  database_version = "{db_ver}"
  region           = "{region}"
  settings {{
    tier = "{tier}"
  }}
}}"""
            hcl_blocks.append(block)

        # --- NEW: GKE Cluster ---
        elif rtype == "google_container_cluster":
            node_count = props.get('initial_node_count', 3)
            machine_type = props.get('machine_type', 'e2-medium')
            region = props.get('region', 'us-central1')
            block = f"""resource "google_container_cluster" "{rname}" {{
  name     = "{rname}"
  location = "{region}"
  node_pool {{
    count  = {node_count}
    name   = "{rname}-pool"
    config {{
      machine_type = "{machine_type}"
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
    }}
  }}
}}
"""
            hcl_blocks.append(block)

        # --- NEW: VM (Compute Engine Instance) ---
        elif rtype == "google_compute_instance":
            machine_type = props.get('machine_type', 'e2-medium')
            disk_size = props.get('disk_size_gb', 10)
            region = props.get('region', 'us-central1')
            block = (
                'resource "google_compute_instance" "' + rname + '" {\n'
                '  name         = "' + rname + '"\n'
                '  machine_type = "' + machine_type + '"\n'
                '  zone         = "' + region + '-a"\n'
                '  disk {\n'
                '    initialize_params {\n'
                '      image_family = "debian-cloud"\n'
                '      image        = "debian-11"\n'
                '      disk_size    = ' + str(disk_size) + '\n'
                '    }\n'
                '  }\n'
                '}\n'
            )
            hcl_blocks.append(block)

        # --- NEW: Load Balancer (Forwarding Rule) ---
        elif rtype == "google_compute_forwarding_rule":
            target = props.get('target', 'http')
            region = props.get('region', 'us-central1')
            scheme = props.get('load_balancing_scheme', 'EXTERNAL')
            block = f"""resource "google_compute_forwarding_rule" "{rname}" {{
  name = "{rname}"
  target = "{target}"
  ip_protocol = "TCP"
  region = "{region}"
  load_balancing_scheme = "{scheme}"
}}
"""
            hcl_blocks.append(block)

        # --- NEW: Global Static IP (for external LB) ---
        elif rtype == "google_compute_global_address":
            block = f"""resource "google_compute_global_address" "{rname}" {{
  name = "{rname}"
  region = "global"
}}
"""
            hcl_blocks.append(block)

        # --- NEW: IAM Member ---
        elif rtype == "google_compute_iam_member":
            member = props.get('member', 'allUsers')
            role = props.get('role', 'roles/viewer')
            resource = props.get('resource', 'vpc')
            block = f"""resource "google_compute_iam_member" "{rname}" {{
  member = "{member}"
  role   = "{role}"
  resource = "{resource}"
}}
"""
            hcl_blocks.append(block)

    return "\n\n".join(hcl_blocks)


if __name__ == "__main__":
    sample_spec = {
      "resources": [
        {"type": "google_compute_vpc", "name": "inferred", "properties": {"auto_create_subnetworks": False}},
        {"type": "google_compute_subnet", "name": "subnet-1", "properties": {"ip_cidr_range": "10.0.1.0/24", "region": "us-central1", "vpc": "inferred"}},
        {"type": "google_compute_subnet", "name": "subnet-2", "properties": {"ip_cidr_range": "10.0.2.0/24", "region": "us-central1", "vpc": "inferred"}},
        {"type": "google_cloud_run_service", "name": "inferred", "properties": {"cpu": "0.7", "memory": "300Mi", "ingress": "ALL"}},
        {"type": "google_sql_database_instance", "name": "inferred", "properties": {"database_version": "POSTGRES_15", "region": "us-central1", "tier": "db-f1-micro", "replica_enabled": True}}
      ]
    }
    print(generate(sample_spec))