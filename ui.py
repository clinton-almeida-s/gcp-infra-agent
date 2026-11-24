import streamlit as st
import json
from agent import run_infra_agent

# UI Configuration
st.set_page_config(page_title="GCP Infra Agent", layout="wide")

st.title("🚀 GCP Infrastructure AI Agent")
st.markdown("Generate valid Terraform, validate it, and get cost estimates in seconds.")

# Sidebar for controls
st.sidebar.header("Configuration")
region = st.sidebar.selectbox("Region", ["us-central1", "us-east1", "europe-west1"], index=0)
mock_mode = st.sidebar.checkbox("Enable Mock Validation", value=True)

# Main input
user_input = st.text_area(
    "Describe your GCP infrastructure",
    value="Create a VPC with 2 subnets (10.0.0.0/16, 10.0.1.0/24 and 10.0.2.0/24), a Cloud Run service with 70/30 split, and a Cloud SQL Postgres instance with a read replica in us-central1.",
    height=150
)

if st.button("Generate Infra Spec"):
    if not user_input:
        st.warning("Please describe your infrastructure first.")
    else:
        with st.spinner("Agent is generating, validating, and estimating..."):
            result = run_infra_agent(user_input)

            # Display results
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("Terraform HCL")
                st.code(result["terraform_hcl"], language="hcl")

                st.subheader("Cost Projection")
                st.metric("Total Monthly USD", f"${result['cost_estimation']['total_monthly_usd']}")

                with st.expander("Cost Breakdown & Assumptions"):
                    st.json(result["cost_estimation"])

            with col2:
                st.subheader("Validation Status")
                if result["validation"]["valid"]:
                    st.success("✅ Configuration is valid!")
                else:
                    st.error("❌ Configuration is invalid")
                    st.text(result["validation"]["error"])

                st.subheader("🚨 Issues & Recommendations")
                if not result["issues"]:
                    st.success("No issues detected!")
                else:
                    for issue in result["issues"]:
                        severity_color = {
                            "HIGH": "🔴",
                            "MEDIUM": "🟠",
                            "LOW": "🟡",
                            "INFO": "🔵"
                        }.get(issue["severity"], "⚪")

                        st.markdown(f"{severity_color} **[{issue['severity']}] {issue['category']}**")
                        st.write(issue["message"])
                        st.info(f"💡 Recommendation: {issue['recommendation']}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built for Platform Engineering")
