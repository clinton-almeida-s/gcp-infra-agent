import json
from parser import parse
from generator import generate
from validator import validate_hcl
from estimator import estimate_cost
from flagger import flag_issues

def run_infra_agent(nl_input: str) -> dict:
    """
    Orchestrates the full GCP Infrastructure Agent pipeline:
    1. Parse natural language into structured resource spec
    2. Generate Terraform HCL from spec
    3. Validate HCL syntax and structure
    4. Estimate monthly GCP costs
    5. Flag security, cost, and reliability issues

    Returns a comprehensive result dictionary for UI or CLI consumption.
    """
    # Step 1: Parse
    spec = parse(nl_input)

    # Step 2: Generate Terraform
    hcl = generate(spec)

    # Step 3: Validate
    validation = validate_hcl(hcl)

    # Step 4: Estimate Cost
    cost = estimate_cost(spec)

    # Step 5: Flag Issues
    issues = flag_issues(spec, hcl)

    return {
        "input_query": nl_input,
        "spec": spec,
        "terraform_hcl": hcl,
        "validation": validation,
        "cost_estimation": cost,
        "issues": issues,
        "status": "success" if validation.get("valid") else "warning"
    }


if __name__ == "__main__":
    prompt = "Create a VPC with 2 subnets (10.0.0.0/16, 10.0.1.0/24 and 10.0.2.0/24), a Cloud Run service with 70/30 split, and a Cloud SQL Postgres instance with a read replica in us-central1."

    print("Running GCP Infrastructure Agent...")
    print(f"Query: {prompt}\n")

    result = run_infra_agent(prompt)

    print("=== 1. PARSED SPEC ===")
    print(json.dumps(result["spec"], indent=2))
    print("\n=== 2. GENERATED TERRAFORM ===")
    print(result["terraform_hcl"])
    print("\n=== 3. VALIDATION ===")
    print(json.dumps(result["validation"], indent=2))
    print("\n=== 4. COST ESTIMATE ===")
    print(f"Total Monthly Cost: ${result['cost_estimation']['total_monthly_usd']} USD")
    print("\n=== 5. FLAGGED ISSUES ===")
    for issue in result["issues"]:
        print(f"[{issue['severity']}] ({issue['category']}) {issue['message']}")
        print(f"   -> Recommendation: {issue['recommendation']}")
