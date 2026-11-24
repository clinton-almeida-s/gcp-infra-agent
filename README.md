# GCP Infrastructure-Code Generation & Validation Agent

An AI agent that converts natural language descriptions of GCP infrastructure into valid Terraform HCL, validates the generated code, projects monthly cost estimates, and flags security/cost/reliability issues.

## Project Goal

Stand out in the job market for Senior GCP Platform/DevOps Engineer roles by demonstrating the ability to build production-grade AI agents that enforce engineering rigor, cost governance, and best-practice guardrails — not just novelty AI chat wrappers.

This project solves the hiring manager problem: many candidates can build AI chat wrappers, but few can build agents that guarantee valid infrastructure code, enforce cost discipline, and surface governance issues.

## Key Differentiators (Interview Talking Points)

1. **Balancing AI creativity with engineering rigor** — the validator step guarantees generated Terraform is actually valid, not just plausibly looking
2. **Why cost estimation before apply matters** — demonstrates financial impact awareness critical for platform roles
3. **Designing the agent to be helpful without being overconfident** — the flagger surfaces issues instead of silently proceeding
4. **Tradeoffs made in scope for the MVP** — started with generate+validate+estimate rather than full `terraform apply`
5. **How this reflects 12 years of GCP experience** — the agent encodes real resource patterns, cost models, and governance practices

## File Structure

```
gcp-infra-agent/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── parser.py             # NL → Structured resource spec
├── generator.py          # Spec → Terraform HCL
├── validator.py          # HCL validation (mock/live)
├── estimator.py          # Monthly cost projection
├── flagger.py            # Security/cost/reliability issue detection
├── agent.py              # Pipeline orchestrator
├── ui.py                 # Streamlit frontend UI
└── design_doc.md         # Full architecture documentation
```

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

```bash
# Clone or cd into project
cd C:\Users\clint\brainstorming_agents\gcp-infra-agent

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Dependencies (`requirements.txt`):
- `streamlit==1.38.0` — UI framework
- `python-dotenv==1.0.0` — Environment variable loading

## Running the Agent

### Start the Streamlit UI

```bash
streamlit run ui.py
```

The UI launches at `http://localhost:8501` (or port 8502 if 8501 is in use).

### CLI Usage

```bash
python -c "from agent import run_infra_agent; result = run_infra_agent('Create a VPC with 2 subnets 10.0.0.0/16 and 10.0.1.0/24, a Cloud Run service with 70/30 split, and a Cloud SQL Postgres instance with a read replica in us-central1'); print(result)"
```

Or use the built-in demo:

```bash
python generator.py
python estimator.py
```

## Supported Prompt Patterns

### 1. VPC + Subnets + Cloud Run + Cloud SQL

```
Create a VPC with 2 subnets (10.0.0.0/16, 10.0.1.0/24 and 10.0.2.0/24), 
a Cloud Run service with 70/30 split, and 
a Cloud SQL Postgres instance with a read replica in us-central1.
```

**Output:** Valid HCL, ~$58.75/month cost, 2 flags (public Cloud Run ingress, shared-core SQL tier)

### 2. GKE Cluster

```
Create a GKE cluster with 3 nodes e2-medium machine type
```

**Output:** `google_container_cluster` HCL, cost estimation (~$197.50/month), applicable flags

### 3. VM Instance

```
Create a VM instance with 20GB disk e2-medium type
```

**Output:** `google_compute_instance` HCL, cost estimate (~$41.50/month)

### 4. Load Balancer with Static External IP

```
Create a load balancer with static external IP
```

**Output:** `google_compute_forwarding_rule` + `google_compute_global_address` HCL, cost (~$5.25/month)

### 5. IAM Member

```
Add IAM role roles/editor for service account my-sa@project.iam.google.com on VPC
```

**Output:** `google_compute_iam_member` HCL, no direct compute cost (governance focus)

## Pipeline Stages

Every prompt executes this deterministic pipeline:

```
User Input (NL)
  |
  v
+-----------------+     +-------------------+
|  Parser (parser.py) | --> | Spec: JSON dict   |
+--------+----------+     +--------+----------+
         |                         |
         v                         v
+-----------------+     +-------------------+
| Generator (gen) | --> | Terraform HCL     |
+--------+--------+     +--------+----------+
         |                         |
         v                         v
+-----------------+     +-------------------+
| Validator (val) | --> | Valid / Error     |
+--------+--------+     +--------+----------+
         |                         |
         v                         v
+-----------------+     +-------------------+
| Estimator (est) | --> | Cost USD / month  |
+--------+--------+     +--------+----------+
         |                         |
         v                         v
+-----------------+     +-------------------+
| Flagger (flag)  | --> | Issues list       |
+-----------------+     +-------------------+

Result JSON consumed by UI (Streamlit) or CLI.
```

## Example Outputs

### Example 1: VPC + Subnets + Cloud Run + Cloud SQL

**Input:**
```
Create a VPC with 2 subnets (10.0.0.0/16, 10.0.1.0/24 and 10.0.2.0/24), 
a Cloud Run service with 70/30 split, and 
a Cloud SQL Postgres instance with a read replica in us-central1.
```

**Generated HCL:**
```hcl
resource "google_compute_vpc" "inferred" {
  name                    = "inferred"
  auto_create_subnetworks = false
}

resource "google_compute_subnet" "subnet-1" {
  name          = "subnet-1"
  ip_cidr_range = "10.0.1.0/24"
  region        = "us-central1"
  vpc_id        = google_compute_vpc.inferred.id
}

resource "google_compute_subnet" "subnet-2" {
  name          = "subnet-2"
  ip_cidr_range = "10.0.2.0/24"
  region        = "us-central1"
  vpc_id        = google_compute_vpc.inferred.id
}

resource "google_cloud_run_service" "inferred" {
  name     = "inferred"
  location = "us-central1"
  template {
    spec {
      containers {
        image = "gcr.io/cloudrun/hello"
        resources {
          limits = {
            cpu    = "0.7"
            memory = "300Mi"
          }
        }
      }
    }
  }
  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "ALL"
    }
  }
}

resource "google_sql_database_instance" "inferred" {
  name             = "inferred"
  database_version = "POSTGRES_15"
  region           = "us-central1"
  settings {
    tier = "db-f1-micro"
  }
}
```

**Cost Projection:** ~$58.75/month
- Cloud Run: $46.08 (0.7 vCPU + 300MiB memory, 730 hrs)
- Cloud SQL (db-f1-micro + read replica): $14.60

**Flagged Issues:**
1. **⚠️ PUBLIC** — Cloud Run ingress set to `ALL` makes service publicly accessible
2. **⚠️ SHARED** — Cloud SQL using shared-core tier (db-f1-micro) for production workloads

### Example 2: GKE Cluster

**Input:**
```
Create a GKE cluster with 3 nodes e2-medium machine type
```

**Generated HCL:**
```hcl
resource "google_container_cluster" "inferred" {
  name     = "inferred"
  location = "us-central1"
  node_pool {
    count  = 3
    name   = "inferred-pool"
    config {
      machine_type = "e2-medium"
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
    }
  }
}
```

**Cost Projection:** ~$197.50/month
- Control plane: $73.00/month
- 3 × e2-medium nodes: $124.50/month (41.50 each)

### Example 3: VM Instance

**Input:**
```
Create a VM instance with 20GB disk e2-medium type
```

**Generated HCL:**
```hcl
resource "google_compute_instance" "test-vm" {
  name         = "test-vm"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
  disk {
    initialize_params {
      image_family = "debian-cloud"
      image        = "debian-11"
      disk_size    = 20
    }
  }
}
```

**Cost Projection:** ~$41.50/month (e2-medium)

### Example 4: Load Balancer with Static External IP

**Input:**
```
Create a load balancer with static external IP
```

**Generated HCL:**
```hcl
resource "google_compute_forwarding_rule" "test-lb" {
  name = "test-lb"
  target = "http"
  ip_protocol = "TCP"
  region = "us-central1"
  load_balancing_scheme = "EXTERNAL"
}

resource "google_compute_global_address" "lb-ip" {
  name = "lb-ip"
  region = "global"
}
```

**Cost Projection:** ~$5.25/month
- Forwarding rule: $0.25/month
- Static global IP: $5.00/month

### Example 5: IAM Member

**Input:**
```
Add IAM role roles/editor for service account my-sa@project.iam.google.com on VPC
```

**Generated HCL:**
```hcl
resource "google_compute_iam_member" "test-iam" {
  member = "service account my-sa@project.iam.google.com"
  role   = "roles/editor"
  resource = "vpc"
}
```

**Cost Projection:** $0.00/month (no direct compute charge)

## Flag Definitions

| Category | Severity | Description |
|----------|----------|-------------|
| **PUBLIC** | important | Public-facing ingress (Cloud Run `ALL`, external LB without restriction) |
| **SHARED** | important | Shared-core tier Cloud SQL for potentially production workloads |
| **BEST_PRACTICE** | nit | VPC auto-created subnets, missing tags, etc. |
| **COST** | nit | High-cost tier selections, premium machine types without justification |

## Post-MVP Enhancements

- Integrate `google-cloud-billing` for live cost estimation via GCP Billing API
- Add `terraform plan` preview and optional `apply` with confirmation prompts
- Extend parser to multi-sentence, cross-resource references
- Containerize with Docker + Cloud Run deployment
- Add authentication / IAM-aware generation (user-provided service account)
- Expand pricing database with regional pricing variations
- Add Terraform provider version pinning

## Author

Built by Clinton Almeida — GCP Platform Engineer with 12+ years experience at Vodafone, focusing on Agentic AI and infrastructure automation.

**Interview ready:** This project is designed to be a standout portfolio piece that demonstrates:
- AI + IaC integration capabilities
- Production-grade engineering rigor (validation, cost estimation, governance)
- Clear documentation and talking points for technical interviews
- Real-world problem solving (generating valid infra code that enforces governance)