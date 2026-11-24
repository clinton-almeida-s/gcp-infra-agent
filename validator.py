import subprocess
import os
import tempfile
import shutil
import json

# --- Configuration ---
MOCK_MODE = True  # Set to False when Terraform CLI is available
TERRAFORM_TIMEOUT = 30  # seconds


def validate_hcl(hcl_content: str) -> dict:
    """
    Validates generated Terraform HCL using 'terraform init' and 'terraform validate'.
    If MOCK_MODE=True (Terraform not installed), simulates a valid/invalid result
    based on HCL patterns to demonstrate the design without requiring terraform.

    Returns:
        {
            "valid": bool,
            "output": str,
            "error": str
        }
    """
    if MOCK_MODE:
        return _mock_validate(hcl_content)

    # Real terraform validation path
    return _real_validate(hcl_content)


def _mock_validate(hcl_content: str) -> dict:
    """
    Simulates terraform validation by checking HCL patterns.
    In a real scenario, this would be replaced by actual terraform CLI calls.
    """
    errors = []
    warnings = []

    # Check for basic HCL structure
    if not hcl_content or not hcl_content.strip():
        return {
            "valid": False,
            "output": "",
            "error": "Empty HCL content provided"
        }

    # Check for resource blocks
    if "resource " not in hcl_content:
        errors.append("No resource blocks found in HCL")

    # Check for provider block
    if "provider " not in hcl_content.lower():
        warnings.append("No provider configuration detected")

    # Check for closing braces balance (very rough check)
    open_braces = hcl_content.count("{")
    close_braces = hcl_content.count("}")
    if open_braces != close_braces:
        warnings.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")

    # Simulate: valid if no critical errors
    valid = len(errors) == 0

    output = ""
    if valid:
        output = "The Terraform configuration is valid.\n"
        output += f"  - {len([l for l in hcl_content.split(chr(10)) if 'resource ' in l])} resource(s) detected"
    else:
        output = "The Terraform configuration has errors.\n"

    if warnings:
        output += "\nWarnings:\n"
        for w in warnings:
            output += f"  - {w}\n"

    return {
        "valid": valid,
        "output": output.strip(),
        "error": "; ".join(errors) if errors else None
    }


def _real_validate(hcl_content: str) -> dict:
    """
    Real Terraform CLI validation.
    Creates a temporary directory, writes HCL + provider config, runs terraform init + validate.
    """
    temp_dir = tempfile.mkdtemp(prefix="gcp_infra_val_")
    try:
        # Write main.tf
        main_tf_path = os.path.join(temp_dir, "main.tf")
        with open(main_tf_path, "w", encoding="utf-8") as f:
            f.write(hcl_content)

        # Write provider config
        provider_tf_path = os.path.join(temp_dir, "provider.tf")
        with open(provider_tf_path, "w", encoding="utf-8") as f:
            f.write("""
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = "dummy-project-id"
  region  = "us-central1"
}
""")

        # 1. Run terraform init -backend=false
        init_res = subprocess.run(
            ["terraform", "init", "-backend=false", "-no-color"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=TERRAFORM_TIMEOUT
        )

        if init_res.returncode != 0:
            return {
                "valid": False,
                "output": init_res.stdout,
                "error": f"Terraform init failed: {init_res.stderr.strip()}"
            }

        # 2. Run terraform validate
        val_res = subprocess.run(
            ["terraform", "validate", "-no-color"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=TERRAFORM_TIMEOUT
        )

        if val_res.returncode != 0:
            return {
                "valid": False,
                "output": val_res.stdout,
                "error": f"Terraform validate failed: {val_res.stderr.strip()}"
            }

        return {
            "valid": True,
            "output": val_res.stdout,
            "error": None
        }

    except FileNotFoundError:
        return {
            "valid": False,
            "output": "",
            "error": "Terraform CLI not found on PATH."
        }
    except Exception as e:
        return {
            "valid": False,
            "output": "",
            "error": str(e)
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Test both modes
    sample_hcl = """
resource "google_compute_vpc" "inferred" {
  name                    = "inferred"
  auto_create_subnetworks = false
}
"""

    print("=== MOCK MODE (Terraform not installed) ===")
    res_mock = validate_hcl(sample_hcl)
    print(f"Valid: {res_mock['valid']}")
    print(f"Output: {res_mock['output'][:100]}...")
    print()

    # Test with invalid HCL
    bad_hcl = "resource \"google_compute_vpc\" \"bad\" { name = \"missing closing brace"
    print("=== Testing bad HCL in mock mode ===")
    res_bad = validate_hcl(bad_hcl)
    print(f"Valid: {res_bad['valid']}")
    print(f"Error: {res_bad['error']}")