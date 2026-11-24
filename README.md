# GCP Infrastructure-Code Generation & Validation Agent

**Project focus:** Senior GCP Platform/DevOps Engineer portfolio piece — AI agent that generates valid Terraform, validates it, and estimates cost before any apply.

## Project Scope (MVP)

### What it does:
1. **Parse** natural language descriptions of GCP infrastructure
2. **Generate** valid Terraform (.tf) code for the requested resources
3. **Validate** Terraform via `terraform init` + `terraform validate`
4. **Estimate** projected monthly cost via GCP Billing API
5. **Flag** issues (invalid properties, cost warnings, security notes)
6. **Present** a clean UI with .tf file + cost + issue list

### What it does NOT do (yet):
- No `terraform apply` (dry-run only)
- No multi-turn conversation memory
- No authentication/authorization flow

### Target role:
Senior GCP Platform/DevOps Engineer — demonstrates AI + IaC + GCP ops + cost governance competence

### Tech stack:
- Python 3.11+
- `google-cloud-billing` for cost estimation
- `terraform` CLI for validation
- `google-generativeai` or `anthropic` for NL → Terraform generation
- Streamlit for UI (leverages existing Streamlit experience)

### Key differentiators vs. typical AI demos:
- **Validator step** ensures generated Terraform is actually valid, not just plausibly looking
- **Cost estimation before apply** shows financial impact awareness — critical for platform roles
- **Issue flagger** surfaces problems instead of silently proceeding
- Encodes real GCP resource patterns from 12 years of platform engineering experience

### Interview talking points this enables:
1. Balancing AI creativity with engineering rigor (validator ensures validity)
2. Why cost estimation before apply matters in platform work
3. Designing the agent to be helpful without being overconfident (flagger surfaces issues)
4. Tradeoffs made in scope for MVP vs. what comes next
5. How this reflects 12 years of GCP experience (encodes real patterns, not just AI hype)

### Next steps:
- [ ] Parse: Implement NL → structured resource spec
- [ ] Generate: Terraform HCL generator
- [ ] Validate: terraform CLI integration
- [ ] Estimate: GCP Billing API cost projection
- [ ] Flagger: Linter-style issue detection
- [ ] UI: Streamlit presentation layer