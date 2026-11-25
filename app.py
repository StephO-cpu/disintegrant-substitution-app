# Streamlit Cloud Deployment Walkthrough + Complete Disintegrant Substitution App
"""

## Part 1: The Complete Streamlit App


Disintegrant Substitution Analyzer
A Streamlit app for comparing local and imported disintegrants.


"""
import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="Disintegrant Substitution Analyzer",
    page_icon="💊",
    layout="wide"
)

# ---- DATA MODEL ----
@dataclass
class Disintegrant:
    name: str
    source: str  # "imported" or "local"
    mechanism: str  # "wicking", "swelling", "both"
    swelling_ratio: float
    cost_usd_per_kg: float
    typical_conc_min_pct: float
    typical_conc_max_pct: float
    works_in_wet_granulation: bool
    regulatory_status: str


# ---- DISINTEGRANT DATABASE ----
DISINTEGRANTS = [
    Disintegrant("Crospovidone", "imported", "wicking", 5, 25.0, 2.0, 5.0, False, "pharmacopoeia"),
    Disintegrant("Sodium Starch Glycolate", "imported", "both", 250, 18.0, 2.0, 6.0, True, "pharmacopoeia"),
    Disintegrant("Croscarmellose Sodium", "imported", "swelling", 150, 22.0, 1.0, 4.0, True, "pharmacopoeia"),
    Disintegrant("Maize Starch (imported)", "imported", "swelling", 15, 2.50, 5.0, 15.0, True, "pharmacopoeia"),
    Disintegrant("Cassava Starch (local)", "local", "swelling", 25, 1.50, 6.0, 12.0, True, "local_requires_qualification"),
    Disintegrant("Potato Starch (imported)", "imported", "swelling", 20, 2.80, 5.0, 15.0, True, "pharmacopoeia"),
    Disintegrant("Rice Starch (local)", "local", "swelling", 18, 2.00, 6.0, 14.0, True, "local_requires_qualification"),
]


# ---- PREDICTION FUNCTIONS ----
def predict_disintegration_time(disintegrant: Disintegrant, concentration_pct: float,
                                 tablet_weight_mg: int = 700, api_solubility_mg_ml: float = 14) -> float:
    """Predict disintegration time in seconds."""
    base_time = 120
    solubility_factor = 1 - min(0.5, api_solubility_mg_ml / 100)
    
    if disintegrant.mechanism == "wicking":
        mechanism_factor = 0.4
    elif disintegrant.mechanism == "both":
        mechanism_factor = 0.5
    else:
        mechanism_factor = 0.7
    
    swelling_factor = max(0.2, 1 - (disintegrant.swelling_ratio / 200))
    
    optimal_conc = (disintegrant.typical_conc_min_pct + disintegrant.typical_conc_max_pct) / 2
    if concentration_pct <= optimal_conc:
        conc_factor = 1 - (concentration_pct / optimal_conc) * 0.7
    else:
        conc_factor = 0.3 - (concentration_pct - optimal_conc) * 0.02
    conc_factor = max(0.15, min(1.0, conc_factor))
    
    predicted_time = base_time * solubility_factor * mechanism_factor * swelling_factor * conc_factor
    predicted_time = max(15, min(180, predicted_time))
    
    return round(predicted_time, 1)


def calculate_savings(current: Disintegrant, candidate: Disintegrant,
                      batch_size_tablets: int, tablet_weight_mg: int,
                      current_conc_pct: float, candidate_conc_pct: float,
                      batches_per_year: int) -> Dict:
    """Calculate cost savings from switching disintegrants."""
    current_qty_kg = (batch_size_tablets * tablet_weight_mg * current_conc_pct / 100) / 1_000_000
    current_cost = current_qty_kg * current.cost_usd_per_kg
    
    candidate_qty_kg = (batch_size_tablets * tablet_weight_mg * candidate_conc_pct / 100) / 1_000_000
    candidate_cost = candidate_qty_kg * candidate.cost_usd_per_kg
    
    savings_per_batch = current_cost - candidate_cost
    annual_savings = savings_per_batch * batches_per_year
    
    return {
        "current_qty_kg_batch": round(current_qty_kg, 3),
        "current_cost_batch_usd": round(current_cost, 2),
        "candidate_qty_kg_batch": round(candidate_qty_kg, 3),
        "candidate_cost_batch_usd": round(candidate_cost, 2),
        "savings_per_batch_usd": round(savings_per_batch, 2),
        "annual_savings_usd": round(annual_savings, 2)
    }


def assess_risk(disintegrant: Disintegrant, predicted_time: float, target_time: float = 60) -> Dict:
    """Assess regulatory and technical risk."""
    risks = []
    risk_score = 0
    
    if predicted_time > target_time:
        risk_score += 40
        risks.append(f"Predicted disintegration ({predicted_time}s) exceeds target ({target_time}s)")
    elif predicted_time > target_time + 30:
        risk_score += 20
        risks.append(f"Disintegration marginal ({predicted_time}s)")
    
    if disintegrant.regulatory_status == "pharmacopoeia":
        risk_score += 5
        risks.append("Low: Pharmacopoeia-listed excipient")
    elif disintegrant.regulatory_status == "local_requires_qualification":
        risk_score += 30
        risks.append("Medium: Supplier qualification required")
    else:
        risk_score += 60
        risks.append("High: Novel excipient requires safety data")
    
    if disintegrant.source == "imported":
        risk_score += 10
        risks.append("Supply chain vulnerability (imported)")
    else:
        risk_score += 0
        risks.append("Supply chain benefit (local)")
    
    if not disintegrant.works_in_wet_granulation:
        risk_score += 25
        risks.append("Cannot be added intra-granularly")
    
    if risk_score <= 20:
        level = "Low"
    elif risk_score <= 50:
        level = "Medium"
    else:
        level = "High"
    
    return {"risk_level": level, "risk_score": risk_score, "risks": risks}


def analyze_substitution(current: Disintegrant, candidates: List[Disintegrant],
                         batch_size: int, tablet_weight_mg: int,
                         current_conc: float, target_disintegration_sec: float,
                         batches_per_year: int):
    """Complete analysis of disintegrant substitution options."""
    results = []
    
    for candidate in candidates:
        if candidate.name == current.name:
            continue
        
        candidate_conc = (candidate.typical_conc_min_pct + candidate.typical_conc_max_pct) / 2
        pred_time = predict_disintegration_time(candidate, candidate_conc, tablet_weight_mg)
        savings = calculate_savings(current, candidate, batch_size, tablet_weight_mg,
                                    current_conc, candidate_conc, batches_per_year)
        risk = assess_risk(candidate, pred_time, target_disintegration_sec)
        
        savings_score = min(100, savings['annual_savings_usd'] / 2000)
        risk_penalty = risk['risk_score'] / 2
        total_score = max(0, savings_score - risk_penalty)
        
        results.append({
            "Disintegrant": candidate.name,
            "Source": candidate.source,
            "Conc (%)": candidate_conc,
            "Predicted Disint (sec)": pred_time,
            "Meets Target?": "Yes" if pred_time <= target_disintegration_sec else "No",
            "Cost ($/kg)": candidate.cost_usd_per_kg,
            "Savings/Batch ($)": savings['savings_per_batch_usd'],
            "Annual Savings ($)": savings['annual_savings_usd'],
            "Risk Level": risk['risk_level'],
            "Total Score": round(total_score, 1),
            "Key Risks": risk['risks'][0][:50] if risk['risks'] else "None"
        })
    
    df = pd.DataFrame(results)
    df = df.sort_values("Total Score", ascending=False)
    return df


# ---- STREAMLIT UI ----
st.title("💊 Disintegrant Substitution Analyzer")
st.markdown("""
Compare local Ghanaian disintegrants against imported alternatives on **disintegration time**, 
**cost savings**, and **regulatory risk**.
""")

# Sidebar: User inputs
st.sidebar.header("⚙️ Input Parameters")

# Current disintegrant selection
disintegrant_names = [d.name for d in DISINTEGRANTS]
current_name = st.sidebar.selectbox(
    "Current Disintegrant",
    disintegrant_names,
    index=0  # Default to Crospovidone
)
current = next(d for d in DISINTEGRANTS if d.name == current_name)

# Current concentration
current_conc = st.sidebar.number_input(
    "Current Concentration (%)",
    min_value=0.5,
    max_value=20.0,
    value=4.0,
    step=0.5
)

# Batch parameters
st.sidebar.subheader("📦 Batch Parameters")
batch_size = st.sidebar.number_input(
    "Batch Size (tablets)",
    min_value=1000,
    max_value=1_000_000,
    value=300_000,
    step=10_000
)

tablet_weight = st.sidebar.number_input(
    "Tablet Weight (mg)",
    min_value=100,
    max_value=2000,
    value=700,
    step=50
)

batches_per_year = st.sidebar.number_input(
    "Batches per Year",
    min_value=1,
    max_value=1000,
    value=200,
    step=10
)

# Target disintegration time
target_time = st.sidebar.slider(
    "Target Disintegration Time (seconds)",
    min_value=15,
    max_value=120,
    value=60,
    step=5
)

# Analyze button
if st.sidebar.button("🔬 Analyze Substitutions", type="primary"):
    # Run analysis
    candidates = [d for d in DISINTEGRANTS if d.name != current.name]
    results_df = analyze_substitution(
        current=current,
        candidates=candidates,
        batch_size=batch_size,
        tablet_weight_mg=tablet_weight,
        current_conc=current_conc,
        target_disintegration_sec=target_time,
        batches_per_year=batches_per_year
    )
    
    # Display results
    st.subheader("📊 Substitution Analysis Results")
    
    # Highlight the top recommendation
    if not results_df.empty:
        top = results_df.iloc[0]
        st.success(f"### 🥇 Top Recommendation: **{top['Disintegrant']}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Disintegration Time", f"{top['Predicted Disint (sec)']} sec")
        with col2:
            st.metric("Annual Savings", f"${top['Annual Savings ($)']:,.0f}")
        with col3:
            st.metric("Risk Level", top['Risk Level'])
        
        st.caption(f"**Key consideration:** {top['Key Risks']}")
    
    # Full results table
    st.subheader("📋 Full Comparison Table")
    st.dataframe(
        results_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Download button
    csv = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name="disintegrant_substitution_analysis.csv",
        mime="text/csv"
    )
    
    # Regulatory workplan
    st.subheader("📄 Regulatory Workplan (for local substitution)")
    st.markdown("""
    1. Supplier qualification audit of local starch processor
    2. Certificate of Analysis (CoA) for 3 lots
    3. Excipient characterization: swelling index, pH, microbial limits, particle size
    4. Compatibility study: API + local starch (40°C/75% RH for 1 month)
    5. Formulation development: trial batches at 6-12% concentrations
    6. Disintegration and dissolution testing (f2 similarity >50 vs. current)
    7. Stability study: 3 pilot batches, 6 months accelerated (40°C/75% RH)
    8. Regulatory submission: Post-approval change (CBE-30) to Ghana FDA
    9. Update specifications and supplier list
    """)
    st.info("**Estimated timeline:** 6-8 months | **Estimated cost:** $8,000 - $12,000")

else:
    # Initial state
    st.info("👈 Configure parameters in the sidebar and click **Analyze Substitutions** to begin.")
    
    # Preview current disintegrant properties
    st.subheader("📌 Current Disintegrant Properties")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Source", current.source.title())
    with col2:
        st.metric("Mechanism", current.mechanism.title())
    with col3:
        st.metric("Cost", f"${current.cost_usd_per_kg}/kg")
    with col4:
        st.metric("Swelling Ratio", f"{current.swelling_ratio}x")


# Footer
st.markdown("---")
st.caption("Built with Streamlit | Data derived from published formulation studies | For educational and portfolio purposes")

