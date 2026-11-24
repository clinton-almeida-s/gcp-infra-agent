import re
import json

def parse(nl: str) -> dict:
    """
    Parse natural language into structured resource spec.

    Supported resource types (MVP + expanded):
    - google_compute_vpc
    - google_compute_subnet
    - google_cloud_run_service
    - google_sql_database_instance
    - google_storage_bucket
    - google_compute_instance  (VM)
    - google_container_cluster  (GKE)
    - google_compute_forwarding_rule + google_compute_global_address  (LB)
    - google_compute_iam_member  (IAM)
    """
    resources = []

    # 1. Detect VPC
    if "vpc" in nl.lower():
        resources.append({
            "type": "google_compute_vpc",
            "name": "inferred",
            "properties": {
                "auto_create_subnetworks": False
            }
        })

    # 2. Detect Subnets and extract CIDRs
    cidr_matches = re.findall(r'10\.\d+\.\d+\.\d+/\d+', nl)
    # Filter out if any is the VPC CIDR (e.g. 10.0.0.0/16)
    subnet_cidrs = [c for c in cidr_matches if not c.endswith('/16')]
    if not subnet_cidrs and cidr_matches:
        subnet_cidrs = cidr_matches[1:] # fallback if no /16 found

    for i, cidr in enumerate(subnet_cidrs, 1):
        resources.append({
            "type": "google_compute_subnet",
            "name": f"subnet-{i}",
            "properties": {
                "ip_cidr_range": cidr,
                "region": "us-central1",
                "vpc": "inferred"
            }
        })

    # 3. Detect Cloud Run
    if "cloud run" in nl.lower():
        cpu, memory = "0.7", "0.3" # default or split
        if "70/30" in nl:
            cpu, memory = "0.7", "0.3"
        resources.append({
            "type": "google_cloud_run_service",
            "name": "inferred",
            "properties": {
                "cpu": cpu,
                "memory": memory,
                "ingress": "ALL"
            }
        })

    # 4. Detect Cloud SQL
    if "cloud sql" in nl.lower():
        replica = "read replica" in nl.lower() or "replica" in nl.lower()
        resources.append({
            "type": "google_sql_database_instance",
            "name": "inferred",
            "properties": {
                "database_version": "POSTGRES_15",
                "region": "us-central1",
                "tier": "db-f1-micro",
                "replica_enabled": replica
            }
        })

    # 5. NEW: GKE Cluster detection
    if "gke" in nl.lower() or "google kubernetes engine" in nl.lower() or "kubernetes cluster" in nl.lower():
        # Extract node count if mentioned
        node_match = re.search(r'(\d+)\s*node', nl, re.IGNORECASE)
        node_count = int(node_match.group(1)) if node_match else 3

        # Extract machine type if mentioned
        machine_match = re.search(r'(e2-medium|n1-standard-1|n1-standard-2|custom-\d+-\d+)', nl, re.IGNORECASE)
        machine_type = machine_match.group(1).lower() if machine_match else "e2-medium"

        resources.append({
            "type": "google_container_cluster",
            "name": "inferred",
            "properties": {
                "initial_node_count": node_count,
                "machine_type": machine_type,
                "region": "us-central1"
            }
        })

    # 6. NEW: VM (Compute Engine instance) detection
    if re.search(r'\b(vm|instance)\b', nl.lower()) and not any(r.get("type") == "google_container_cluster" for r in resources):
        # Check if it's not already a GKE context
        # Extract machine type if mentioned
        machine_match = re.search(r'(e2-medium|n1-standard-1|n1-standard-2|custom-\d+-\d+)', nl, re.IGNORECASE)
        machine_type = machine_match.group(1).lower() if machine_match else "e2-medium"

        # Check for custom disk size
        disk_match = re.search(r'(\d+)\s*gb|(\d+)\s*gib', nl, re.IGNORECASE)
        disk_size = int(disk_match.group(1) or disk_match.group(2)) if disk_match else 10

        resources.append({
            "type": "google_compute_instance",
            "name": "inferred",
            "properties": {
                "machine_type": machine_type,
                "disk_size_gb": disk_size,
                "region": "us-central1"
            }
        })

    # 7. NEW: Load Balancer detection
    if any(kw in nl.lower() for kw in ["load balancer", "lb", "forwarding rule"]):
        # Check if target is specified
        target_match = re.search(r'(web|ssl|ssl-proxy|tcp-proxy|internal)', nl, re.IGNORECASE)
        target = target_match.group(1).lower() if target_match else "http"

        # Check for static IP
        has_static_ip = "static ip" in nl.lower() or "externai ip" in nl.lower() or "external ip" in nl.lower()

        # Add forwarding rule + global address if we don't have one yet
        # We'll add a forwarding rule reference; the actual address resource added separately if needed
        resources.append({
            "type": "google_compute_forwarding_rule",
            "name": "inferred",
            "properties": {
                "target": target,
                "region": "us-central1",
                "load_balancing_scheme": "EXTERNAL" if has_static_ip else "INTERNAL"
            }
        })

        # Add global static address if static IP requested
        if has_static_ip:
            resources.append({
                "type": "google_compute_global_address",
                "name": "lb-ip",
                "properties": {
                    "name": "lb-ip",
                    "region": "global"
                }
            })

    # 8. NEW: IAM member detection
    if any(kw in nl.lower() for kw in ["iam", "service account", "grant access", "permissions"]):
        # Check who is being granted access
        who_match = re.search(r'(service account [a-z0-9-]+|user [a-z0-9-]+|group [a-z0-9-]+|allUsers|allAuthenticatedUsers)', nl, re.IGNORECASE)
        who = who_match.group(1).lower() if who_match else "allUsers"

        # Check what role
        role_match = re.search(r'role [a-z0-9_-]+|roles/[a-z0-9_-]+', nl, re.IGNORECASE)
        role = role_match.group(0).lower() if role_match else "roles/viewer"

        # Check on what resource
        resource_match = re.search(r'(on [a-z]+|for [a-z]+|of [a-z]+)', nl, re.IGNORECASE)
        resource_context = resource_match.group(1).lower() if resource_match else "vpc"

        resources.append({
            "type": "google_compute_iam_member",
            "name": "inferred",
            "properties": {
                "member": who,
                "role": role,
                "resource": resource_context
            }
        })

    return {"resources": resources}

if __name__ == "__main__":
    sample = "Create a VPC with 2 subnets (10.0.0.0/16, 10.0.1.0/24 and 10.0.2.0/24), a Cloud Run service with 70/30 split, and a Cloud SQL Postgres instance with a read replica in us-central1."
    print(json.dumps(parse(sample), indent=2))