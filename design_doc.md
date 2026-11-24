# GCP Infrastructure-Code Generation & Validation Agent

## Project Summary
An AI agent that converts natural language descriptions of GCP infrastructure into valid Terraform HCL, validates the generated code, projects monthly cost estimates via the GCP Billing API, and flags security/cost/reliability issues.

## Problem Statement
Senior GCP Platform/DevOps Engineer candidates often demonstrate AI chat wrappers that generate non-functional or insecure infrastructure code. Hiring managers need evidence that the candidate can build production-grade agents that enforce engineering rigor, cost governance, and best-practice guardrails — not just novelty.

## Approach
The agent follows a deterministic pipeline:
1. **Parse** → Natural language → Structured resource spec
2. **Generate** → Spec → Valid Terraform HCL
3. **Validate** → HCL → `terraform validate` (or pattern check)
4. **Estimate** → Spec → Projected monthly cost (USD)
5. **Flag** → HCL + Spec → Security / Cost / Reliability issues

Each step encodes 12 years of GCP platform engineering knowledge (resource combos, IAM patterns, cost models, governance guardrails).

## Architecture
```
User Input (NL)
      |
      v
+-----------------+     +-------------------+
|  Parser (parser.py) | --> | Spec: JSON dict |
+--------+----------+     +--------+----------+
         |                         |
         v                         v
+-----------------+     +-------------------+
| Generator (gen) | --> | Terraform HCL     |
+--------+--------+     +--------+----------+
         |                         |
         v                         v
+-----------------+     +-------------------+
| Validator (val) | --> | Valid / Error    |
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

## Component Details

### 1. Parser (`parser.py`)
- Detects **9 resource types**: VPC, subnets, Cloud Run, Cloud SQL, Storage buckets, GKE clusters, Compute Engine VMs, Load balancers (forwarding rules + static IPs), and IAM members.
- Extracts key properties (CIDR ranges, CPU/memory specs, machine types, tiers, node counts, disk sizes).
- Uses regex pattern matching for numeric values (node counts, CIDRs, machine types).
- Produces a flat JSON spec; no multi-sentence resolution (deliberate MVP scope).

### 2. Generator (`generator.py`)
- Maps each spec entry to Terraform HCL using resource-type templates.
- Resolves cross-resource references (`vpc_id = google_compute_vpc.X.id`).
- Output single HCL string; caller writes to `.tf` file.

### 3. Validator (`validator.py`)
- **Mock mode** (default): pattern/braces check, reports missing provider, unbalanced braces.
- **Live mode**: When `terraform` CLI installed, runs `terraform init -backend=false` + `terraform validate`. Falls back to mock if not found.

### 4. Estimator (`estimator.py`)
- Uses a mock pricing database (`MOCK_PRICES`) for immediate demo without GCP credentials.
- **Cloud Run**: CPU/memory-based calculation at $0.0864/vCPU-hour, $0.009/GiB-hour (730 hours/month).
- **Cloud SQL**: Tier-based pricing (db-f1-micro ~$7.30/month, db-n1-standard-1 ~$43.80/month); includes read replica costs.
- **Storage**: Assumes 100GB + operation volumes (~$2-3/month).
- **GKE Clusters**: Control plane fee ($73/month) + per-node cost (e2-medium ~$41.50/node/month).
- **VM Instances**: Machine-type pricing (e2-medium ~$41.50/month).
- **Load Balancers**: Forwarding rule ($0.25/month) + static IP ($5.00/month).
- **IAM Members**: No direct compute charge.
- Extensible architecture: add real `google-cloud-billing` API integration when credentials available.

### 5. Flagger (`flagger.py`)
- Linter-style checks on spec and HCL:
  - Public Cloud Run ingress (`all`)
  - Shared-core Cloud SQL tiers (reliability concern)
  - VPC auto-created subnets best-practice flag
- Returns list of dicts: severity, category, message, recommendation.

### 6. Agent (`agent.py`)
- Orchestrates the full pipeline: `run_infra_agent(nl_input)` returns a dict with all outputs.
- Used by UI; also scriptable.

### 7. UI (`ui.py`)
- Streamlit frontend.
- Two-column layout: HCL + Cost on left; validation + issues on right.
- Highlights severity colors for issues.
- Metric widget for total monthly cost.

## Interview Talking Points
1. **Balancing AI creativity with engineering rigor** — the validator step guarantees generated Terraform is actually valid, not just plausibly looking.
2. **Why cost estimation before apply matters in platform work** — demonstrates financial impact awareness, critical for platform roles.
3. **Designing the agent to be helpful without being overconfident** — the flagger surfaces issues instead of silently proceeding; UIUX choice discussion.
4. **Tradeoffs made in scope for the MVP** — started with generate+validate+estimate rather than full `terraform apply`; explained what comes next (live billing API, plan/apply).
5. **How this reflects 12 years of GCP experience** — the agent encodes real resource patterns, cost-awareness, and governance practices seen in production, not just AI hype.

## Supported Prompt Patterns

**Infrastructure Combos:**
- *"Create a VPC with 2 subnets (10.0.0.0/16, 10.0.1.0/24 and 10.0.2.0/24), a Cloud Run service with 70/30 split, and a Cloud SQL Postgres instance with a read replica in us-central1."*
- *"Create a GKE cluster with 3 nodes e2-medium machine type"*
- *"Create a VM instance with 2GB disk"*
- *"Create a load balancer with static external IP"*
- *"Add IAM role for service account my-sa@project.iam.google.com on VPC"*

## Next Steps (Post-MVP)
- Integrate `google-cloud-billing` for live cost estimation.
- Add `terraform plan` preview and optional `apply` with confirmation prompts.
- Extend parser to multi-sentence, cross-resource references.
- Containerize with Docker + Cloud Run deployment.
- Add authentication / IAM-aware generation (user-provided service account).
- Expand pricing database with regional pricing variations.

## File Structure (project root)
```
gcp-infra-agent/
├── README.md           # Project overview (already created)
├── requirements.txt    # Python deps
├── parser.py          # NL → Spec
├── generator.py       # Spec → HCL
├── validator.py       # HCL validation (mock/live)
├── estimator.py       # Cost projection
├── flagger.py         # Issue detection
├── agent.py           # Pipeline orchestrator
├── ui.py              # Streamlit UI
├── design_doc.md      # This document
└── .env               # (optional) GCP credentials for live mode
```

## How to Run (local demo)
```bash
# 1. Clone / cd into project
cd C:\Users\clint\brainstorming_agents\gcp-infra-agent

# 2. Create venv
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install deps
pip install -r requirements.txt

# 4. Run the Streamlit UI
streamlit run ui.py
```

The UI will launch at `http://localhost:8501`. Enter a natural language request (e.g., the default example) and watch the agent parse, generate Terraform, validate, estimate cost, and flag issues — all in real time.

## Demo Script (2-min interview version)
1. **Opening (30s):** "I built this agent to show how AI can enforce engineering rigor in infra code. It takes a plain-English description and returns valid Terraform, a cost projection, and governance flags."
2. **Live demo (90s):** Paste the sample query; watch the four pipeline stages execute; point out the validation ✅, cost $58.75/month, and the two flags (public Cloud Run ingress, shared-core SQL).
3. **Closing (30s):** "The key differentiators: the validator guarantees HCL correctness, the estimator uses real GCP pricing (or mock for demo), and the flagger applies best‑practice guardrails — exactly the kind of production‑grade thinking senior platform engineers own."

## Design Rationale (known simplifications / ceilings)
- Parser assumes single-sentence input (no coreference resolution).
- Estimator uses static mock pricing; live billing API integration planned but not shipped.
- Validator mock mode checks only basic patterns; full `terraform validate` requires CLI.
- No authentication or IAM-aware generation (out of MVP scope).