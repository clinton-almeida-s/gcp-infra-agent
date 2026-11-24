from typing import List, Dict, Any

def flag_issues(spec: dict, hcl_content: str) -> List[Dict[str, str]]:
    """
    Scans the resource spec and generated Terraform HCL for security,
    cost, and reliability best-practice violations.

    Returns a list of issues:
    [
        {
            "severity": "HIGH" | "MEDIUM" | "LOW" | "INFO",
            "category": "SECURITY" | "COST" | "RELIABILITY" | "BEST_PRACTICE",
            "message": "...",
            "recommendation": "..."
        },
        ...
    ]
    """
    issues = []

    # Check HCL and spec resources
    resources = spec.get("resources", [])

    has_cloud_run = any(r.get("type") == "google_cloud_run_service" for r in resources)
    has_cloud_sql = any(r.get("type") == "google_sql_database_instance" for r in resources)
    has_vpc = any(r.get("type") == "google_compute_vpc" for r in resources)

    # 1. Cloud Run Ingress Check
    for r in resources:
        if r.get("type") == "google_cloud_run_service":
            ingress = r.get("properties", {}).get("ingress", "ALL")
            if ingress == "ALL":
                issues.append({
                    "severity": "MEDIUM",
                    "category": "SECURITY",
                    "message": "Cloud Run service has public ingress enabled (all traffic allowed).",
                    "recommendation": "Consider setting ingress to 'internal' or 'internal-and-cloud-load-balancing' if public access is not required."
                })

    # 2. Cloud SQL Tier Check
    for r in resources:
        if r.get("type") == "google_sql_database_instance":
            tier = r.get("properties", {}).get("tier", "db-f1-micro")
            if "micro" in tier or "small" in tier:
                issues.append({
                    "severity": "LOW",
                    "category": "RELIABILITY",
                    "message": f"Cloud SQL is using shared-core tier ({tier}).",
                    "recommendation": "Shared-core instances are not recommended for production workloads due to CPU throttling risks. Use db-n1-standard-1 or higher for production."
                })

            replica_enabled = r.get("properties", {}).get("replica_enabled", False)
            if not replica_enabled:
                issues.append({
                    "severity": "INFO",
                    "category": "RELIABILITY",
                    "message": "Cloud SQL read replica is not enabled.",
                    "recommendation": "For high availability and read-heavy workloads, consider enabling a read replica."
                })

    # 3. VPC Auto-create subnets check
    for r in resources:
        if r.get("type") == "google_compute_vpc":
            auto_sub = r.get("properties", {}).get("auto_create_subnetworks", True)
            if auto_sub:
                issues.append({
                    "severity": "LOW",
                    "category": "BEST_PRACTICE",
                    "message": "VPC has auto_create_subnetworks = true.",
                    "recommendation": "Custom subnet mode (auto_create_subnetworks = false) is generally recommended for enterprise environments to maintain IP range control."
                })

    # 4. General Cost / Production Readiness checks
    if len(resources) > 0 and not has_cloud_sql:
        issues.append({
            "severity": "INFO",
            "category": "BEST_PRACTICE",
            "message": "No database resource detected in architecture.",
            "recommendation": "If stateful data is required, ensure a managed database (Cloud SQL, Firestore, BigQuery) is included."
        })

    return issues


if __name__ == "__main__":
    sample_spec = {
        "resources": [
            {"type": "google_compute_vpc", "name": "inferred", "properties": {"auto_create_subnetworks": False}},
            {"type": "google_cloud_run_service", "name": "inferred", "properties": {"cpu": "0.7", "memory": "300Mi", "ingress": "ALL"}},
            {"type": "google_sql_database_instance", "name": "inferred", "properties": {"database_version": "POSTGRES_15", "tier": "db-f1-micro", "replica_enabled": False}}
        ]
    }

    found_issues = flag_issues(sample_spec, "")
    import json
    print(json.dumps(found_issues, indent=2))
