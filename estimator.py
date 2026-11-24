import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

# --- Configuration ---
MOCK_PRICING = True  # Set to False when GCP credentials are available

# Mock pricing data (monthly USD estimates, us-central1)
# Source: GCP Pricing Calculator approximations
MOCK_PRICES = {
    # VPC - no charge
    "google_compute_vpc": 0.0,

    # Subnet - no direct charge
    "google_compute_subnet": 0.0,

    # Cloud Run - depends on CPU/memory/requests
    # Estimate: $0.00002400 per vCPU-second, $0.00000250 per GiB-second
    # Assuming 730 hours/month, 100% utilization for max estimate
    "google_cloud_run_service": {
        "base": 0.0,  # Calculated from CPU/memory
        "cpu_price_per_hour": 0.00002400 * 3600,  # $0.0864 per vCPU-hour
        "memory_price_per_hour": 0.00000250 * 3600,  # $0.009 per GiB-hour
        "hours_per_month": 730
    },

    # Cloud SQL - depends on tier
    "google_sql_database_instance": {
        "db-f1-micro": 7.30,      # Shared-core, ~$7.30/month
        "db-g1-small": 29.20,     # 1 vCPU, 1.7GB
        "db-n1-standard-1": 43.80, # 1 vCPU, 3.75GB
        "db-n1-standard-2": 87.60, # 2 vCPU, 7.5GB
        "db-custom-1-3840": 36.50, # Custom 1 vCPU, 3.75GB
    },

    # Cloud Storage - Standard class
    "google_storage_bucket": {
        "storage_per_gb_month": 0.020,
        "class_a_ops_per_10k": 0.05,
        "class_b_ops_per_10k": 0.004,
        "network_egress_per_gb": 0.12,
    },

    # NEW: GKE Cluster pricing (per cluster, us-central1)
    # GKE pricing includes: control plane (fixed) + node costs (per node)
    "google_container_cluster": {
        "control_plane_monthly": 0.0,  # GKE control plane has free tier/trial; charged separately by Google
        "e2-medium_node_monthly": 41.50,  # e2-medium ~$41.50/month in us-central1
        "n1_standard_1_node_monthly": 69.50,  # n1-standard-1 ~$69.50/month
        "default_node_type": "e2-medium",
        "default_node_count": 3,
    },

    # NEW: VM (Compute Engine) pricing per month, us-central1
    "google_compute_instance": {
        "e2-medium_monthly": 41.50,    # 2 vCPU, 4GB memory
        "n1_standard_1_monthly": 69.50, # 1 vCPU, 3.75GB
        "custom_2gb_monthly": 25.00,    # Custom small instance
    },

    # NEW: Load Balancer (Forwarding Rule + IP) pricing per month
    "google_compute_forwarding_rule": {
        "monthly_per_rule": 0.25,  # $0.25 per forwarding rule
        "monthly_static_ip": 5.00,  # $5.00 per static IP address (first 10 free in some contexts)
    },

    # NEW: IAM member - no direct compute charge, but governance cost
    "google_compute_iam_member": 0.0,
}

@dataclass
class ResourceCost:
    resource_type: str
    resource_name: str
    monthly_cost: float
    breakdown: Dict[str, float]
    assumptions: List[str]


def estimate_cost(spec: dict) -> dict:
    """
    Estimate monthly costs for resources in the spec.

    Returns:
        {
            "total_monthly_usd": float,
            "resources": [
                {
                    "type": str,
                    "name": str,
                    "monthly_cost": float,
                    "breakdown": {...},
                    "assumptions": [...]
                },
                ...
            ],
            "currency": "USD",
            "region": "us-central1",
            "mode": "mock" | "live"
        }
    """
    if MOCK_PRICING:
        return _mock_estimate(spec)
    return _live_estimate(spec)


def _mock_estimate(spec: dict) -> dict:
    """Mock estimation using hardcoded pricing data."""
    resources = []
    total = 0.0

    for res in spec.get("resources", []):
        rtype = res.get("type")
        rname = res.get("name")
        props = res.get("properties", {})

        if rtype == "google_compute_vpc":
            cost = _estimate_vpc()

        elif rtype == "google_compute_subnet":
            cost = _estimate_subnet()

        elif rtype == "google_cloud_run_service":
            cost = _estimate_cloud_run(props)

        elif rtype == "google_sql_database_instance":
            cost = _estimate_cloud_sql(props)

        elif rtype == "google_storage_bucket":
            cost = _estimate_storage(props)

        elif rtype == "google_container_cluster":
            cost = _estimate_gke_cluster(props)

        elif rtype == "google_compute_instance":
            cost = _estimate_vm(props)

        elif rtype == "google_compute_forwarding_rule":
            cost = _estimate_lb_rule(props)

        elif rtype == "google_compute_global_address":
            cost = _estimate_static_ip(props)

        elif rtype == "google_compute_iam_member":
            cost = _estimate_iam()

        else:
            cost = ResourceCost(
                resource_type=rtype,
                resource_name=rname,
                monthly_cost=0.0,
                breakdown={},
                assumptions=[f"No pricing model for {rtype}"]
            )

        resources.append({
            "type": rtype,
            "name": rname,
            "monthly_cost": cost.monthly_cost,
            "breakdown": cost.breakdown,
            "assumptions": cost.assumptions
        })
        total += cost.monthly_cost

    return {
        "total_monthly_usd": round(total, 2),
        "resources": resources,
        "currency": "USD",
        "region": "us-central1",
        "mode": "mock"
    }


# --- Estimation functions for new resource types ---

def _estimate_vpc() -> ResourceCost:
    """Estimate VPC - no direct charge."""
    return ResourceCost(
        resource_type="google_compute_vpc",
        resource_name="VPC",
        monthly_cost=0.0,
        breakdown={},
        assumptions=["VPC itself has no charge", "Only attached resources (subnets, firewall rules, etc.) incur costs"]
    )


def _estimate_subnet() -> ResourceCost:
    """Estimate Subnet - no direct charge."""
    return ResourceCost(
        resource_type="google_compute_subnet",
        resource_name="Subnet",
        monthly_cost=0.0,
        breakdown={},
        assumptions=["Subnet itself has no charge", "Network egress from VMs/Load Balancers incurs costs"]
    )


def _estimate_cloud_run(props: dict) -> ResourceCost:
    """Estimate Cloud Run cost based on CPU/memory allocation."""
    cpu = float(props.get("cpu", "1"))
    memory_str = props.get("memory", "512Mi")
    memory_gib = _parse_memory_to_gib(memory_str)

    prices = MOCK_PRICES["google_cloud_run_service"]
    cpu_cost = cpu * prices["cpu_price_per_hour"] * prices["hours_per_month"]
    memory_cost = memory_gib * prices["memory_price_per_hour"] * prices["hours_per_month"]
    total = cpu_cost + memory_cost

    return ResourceCost(
        resource_type="google_cloud_run_service",
        resource_name="Cloud Run Service",
        monthly_cost=round(total, 2),
        breakdown={
            "cpu": round(cpu_cost, 2),
            "memory": round(memory_cost, 2)
        },
        assumptions=[
            f"CPU: {cpu} vCPU",
            f"Memory: {memory_str} ({memory_gib:.2f} GiB)",
            "100% utilization for 730 hours/month (max estimate)",
            "No request-based charges included",
            "Region: us-central1"
        ]
    )


def _estimate_gke_cluster(props: dict) -> ResourceCost:
    """Estimate GKE Cluster monthly cost."""
    node_count = props.get('initial_node_count', 3)
    node_type = props.get('machine_type', 'e2-medium')

    # Base node cost - pricing keys keep hyphens
    price_key = f"{node_type}_node_monthly"
    default_price_key = f"{MOCK_PRICES['google_container_cluster']['default_node_type']}_node_monthly"
    node_unit_price = MOCK_PRICES["google_container_cluster"].get(price_key, MOCK_PRICES["google_container_cluster"][default_price_key])
    node_cost = node_unit_price * node_count

    # Control plane cost (GKE has a cost, approx $0.10/hour for standard cluster in us-central1 ~ $73/month)
    control_plane = 73.00  # Approximate control plane cost

    total = control_plane + node_cost

    # Determine node type name for breakdown
    node_type_names = {
        "e2-medium": "e2-medium",
        "n1-standard-1": "n1-standard-1",
    }
    node_type_name = node_type_names.get(node_type, node_type)

    breakdown = {
        "control_plane": round(control_plane, 2),
        f"{node_type_name}_nodes": round(node_cost, 2),
    }

    assumptions = [
        f"Cluster with {node_count} node(s)",
        f"Node type: {node_type_name}",
        "Region: us-central1",
        "Control plane fee included (approx $73/month)",
        f"Node cost: ${node_unit_price:.2f}/month per node",
        "No auto-scaling or GPU costs included"
    ]

    return ResourceCost(
        resource_type="google_container_cluster",
        resource_name="GKE Cluster",
        monthly_cost=round(total, 2),
        breakdown=breakdown,
        assumptions=assumptions
    )


def _estimate_vm(props: dict) -> ResourceCost:
    """Estimate Compute Engine VM monthly cost."""
    machine_type = props.get('machine_type', 'e2-medium')

    # Extract from pricing dict
    price_key = f"{machine_type}_monthly"
    vm_unit_price = MOCK_PRICES["google_compute_instance"].get(price_key, MOCK_PRICES["google_compute_instance"]["e2-medium_monthly"])

    total = vm_unit_price

    breakdown = {
        f"{machine_type}_instance": round(vm_unit_price, 2)
    }

    assumptions = [
        f"VM instance: {machine_type}",
        "Region: us-central1",
        "Includes sustained use discounts (assumed)",
        "No persistent disk charges included (add $10-50 depending on size)",
        "No networking egress charges included"
    ]

    return ResourceCost(
        resource_type="google_compute_instance",
        resource_name="VM Instance",
        monthly_cost=round(total, 2),
        breakdown=breakdown,
        assumptions=assumptions
    )


def _estimate_lb_rule(props: dict) -> ResourceCost:
    """Estimate Load Balancer forwarding rule monthly cost."""
    monthly_per_rule = MOCK_PRICES["google_compute_forwarding_rule"]["monthly_per_rule"]
    has_static_ip = props.get('load_balancing_scheme', 'EXTERNAL') == 'EXTERNAL'

    total = monthly_per_rule

    if has_static_ip:
        total += MOCK_PRICES["google_compute_forwarding_rule"]["monthly_static_ip"]

    breakdown = {
        "forwarding_rule": round(monthly_per_rule, 2),
    }
    if has_static_ip:
        breakdown["static_ip"] = round(MOCK_PRICES["google_compute_forwarding_rule"]["monthly_static_ip"], 2)

    assumptions = [
        "1 forwarding rule",
        f"Static IP: {'enabled' if has_static_ip else 'not included'}",
        "Region: us-central1",
        "No backend service or health check charges included",
        "No traffic processing fees included"
    ]

    return ResourceCost(
        resource_type="google_compute_forwarding_rule",
        resource_name="Load Balancer Fronting Rule",
        monthly_cost=round(total, 2),
        breakdown=breakdown,
        assumptions=assumptions
    )


def _estimate_static_ip(props: dict) -> ResourceCost:
    """Estimate static/global IP address monthly cost."""
    monthly_static_ip = MOCK_PRICES["google_compute_forwarding_rule"]["monthly_static_ip"]

    total = monthly_static_ip

    breakdown = {
        "static_global_ip": round(monthly_static_ip, 2)
    }

    assumptions = [
        "1 global static IP address",
        "Region: global",
        "First 100 IPs free in some Google accounts; priced after that",
        "No forwarding rule or load balancing charges included"
    ]

    return ResourceCost(
        resource_type="google_compute_global_address",
        resource_name="Static Global IP",
        monthly_cost=round(total, 2),
        breakdown=breakdown,
        assumptions=assumptions
    )


def _estimate_iam() -> ResourceCost:
    """Estimate IAM member - no direct compute charge."""
    total = 0.0

    breakdown = {}

    assumptions = [
        "IAM member assignment has no direct compute cost",
        "Governance/risk-management cost is organizational, not per-resource",
        "No additional compute charges for this assignment"
    ]

    return ResourceCost(
        resource_type="google_compute_iam_member",
        resource_name="IAM Member",
        monthly_cost=0.0,
        breakdown=breakdown,
        assumptions=assumptions
    )


def _estimate_cloud_sql(props: dict) -> ResourceCost:
    """Estimate Cloud SQL cost based on instance tier."""
    tier = props.get("tier", "db-f1-micro")
    replica = props.get("replica_enabled", False)

    base_cost = MOCK_PRICES["google_sql_database_instance"].get(tier, 0.0)
    replica_cost = base_cost if replica else 0.0  # Read replica costs same as primary
    total = base_cost + replica_cost

    breakdown = {"primary": base_cost}
    if replica:
        breakdown["read_replica"] = replica_cost

    return ResourceCost(
        resource_type="google_sql_database_instance",
        resource_name="Cloud SQL Instance",
        monthly_cost=round(total, 2),
        breakdown=breakdown,
        assumptions=[
            f"Tier: {tier}",
            f"Region: us-central1",
            "Includes instance + storage (10GB default)",
            f"Read replica: {'enabled' if replica else 'disabled'}",
            "No backup storage charges included"
        ]
    )


def _estimate_storage(props: dict) -> ResourceCost:
    """Estimate Cloud Storage cost."""
    # Assume 100GB stored, 1M Class A ops, 10M Class B ops
    storage_gb = 100
    class_a_ops = 1_000_000
    class_b_ops = 10_000_000

    prices = MOCK_PRICES["google_storage_bucket"]
    storage_cost = storage_gb * prices["storage_per_gb_month"]
    class_a_cost = (class_a_ops / 10_000) * prices["class_a_ops_per_10k"]
    class_b_cost = (class_b_ops / 10_000) * prices["class_b_ops_per_10k"]
    total = storage_cost + class_a_cost + class_b_cost

    return ResourceCost(
        resource_type="google_storage_bucket",
        resource_name="Cloud Storage Bucket",
        monthly_cost=round(total, 2),
        breakdown={
            "storage": round(storage_cost, 2),
            "class_a_operations": round(class_a_cost, 2),
            "class_b_operations": round(class_b_cost, 2)
        },
        assumptions=[
            "100 GB stored (Standard class)",
            "1M Class A operations/month",
            "10M Class B operations/month",
            "No egress charges included"
        ]
    )


def _parse_memory_to_gib(memory_str: str) -> float:
    """Parse memory string like '512Mi', '1Gi', '2G' to GiB."""
    memory_str = memory_str.strip().upper()

    if memory_str.endswith("GI"):
        return float(memory_str[:-2])
    elif memory_str.endswith("MI"):
        return float(memory_str[:-2]) / 1024
    elif memory_str.endswith("KI"):
        return float(memory_str[:-2]) / (1024 * 1024)
    elif memory_str.endswith("G"):
        return float(memory_str[:-1])
    elif memory_str.endswith("M"):
        return float(memory_str[:-1]) / 1024
    elif memory_str.endswith("K"):
        return float(memory_str[:-1]) / (1024 * 1024)
    else:
        # Assume bytes if no unit
        try:
            return float(memory_str) / (1024**3)
        except ValueError:
            return 0.5  # Default 512Mi


def _live_estimate(spec: dict) -> dict:
    """
    Live estimation using GCP Billing API (Cloud Billing Catalog API).
    Requires: GOOGLE_APPLICATION_CREDENTIALS with billing.accounts.listSkus permission
    """
    # TODO: Implement when GCP credentials are available
    # Would use google-cloud-billing library
    return {
        "total_monthly_usd": 0.0,
        "resources": [],
        "currency": "USD",
        "region": "us-central1",
        "mode": "live",
        "error": "Live estimation not yet implemented - requires GCP credentials"
    }


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

    result = estimate_cost(sample_spec)
    print(json.dumps(result, indent=2))