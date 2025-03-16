import streamlit as st
import pandas as pd

# === PAGE CONFIG ===
st.set_page_config(page_title="Admin Panel - Linear Lightspec Optimiser", layout="wide")
st.title("🛠️ Admin Panel - Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'admin_mode' not in st.session_state:
    st.session_state['admin_mode'] = True
if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"

# === Default Settings per Tier ===
tier_defaults = {
    "Core": {"ecg_type": "Fixed Output", "ecg_max_output": 150, "ecg_stress": 100, "led_stress": 350},
    "Professional": {"ecg_type": "DALI-2", "ecg_max_output": 140, "ecg_stress": 85, "led_stress": 300},
    "Advanced": {"ecg_type": "Wireless DALI-2", "ecg_max_output": 120, "ecg_stress": 75, "led_stress": 250},
    "Bespoke": {"ecg_type": "Custom (Editable)", "ecg_max_output": None, "ecg_stress": None, "led_stress": None}
}

# === SIDEBAR - PRODUCT TIER SELECTION ===
st.sidebar.header("⚙️ Product Tier Selection")
selected_tier = st.sidebar.selectbox("Select Product Tier", list(tier_defaults.keys()), index=1)
st.session_state['tier'] = selected_tier

# === DISPLAY CURRENT TIER SETTINGS ===
st.subheader(f"🔧 {selected_tier} Tier Configuration")

if selected_tier != "Bespoke":
    defaults = tier_defaults[selected_tier]
    st.write(f"**ECG Type:** {defaults['ecg_type']}")
    st.write(f"**ECG Max Output (W):** {defaults['ecg_max_output']}")
    st.write(f"**ECG Stress Loading (%):** {defaults['ecg_stress']}")
    st.write(f"**LED Max Current per Chip (mA):** {defaults['led_stress']}")
else:
    # Custom fields exposed for bespoke tier
    st.session_state['ecg_max_output'] = st.number_input(
        "Custom ECG Max Output (W)", min_value=10, max_value=300, step=1
    )
    st.session_state['ecg_stress'] = st.slider(
        "Custom ECG Stress Loading (%)", min_value=50, max_value=100, step=1
    )
    st.session_state['led_stress'] = st.slider(
        "Custom LED Max Current (mA)", min_value=100, max_value=400, step=1
    )

    reason = st.text_area("Reason for Custom Bespoke Settings")
    if not reason:
        st.error("You must provide a reason before proceeding.")

# === OUTPUT TABLE FOR VERIFICATION ===
tier_data = []
for tier, values in tier_defaults.items():
    tier_data.append({
        "Product Tier": tier,
        "ECG Type": values['ecg_type'],
        "ECG Max Output (W)": values['ecg_max_output'] if values['ecg_max_output'] else "Custom",
        "ECG Stress (%)": values['ecg_stress'] if values['ecg_stress'] else "Custom",
        "LED Max Current (mA)": values['led_stress'] if values['led_stress'] else "Custom"
    })

st.subheader("📋 Tier Default Settings Reference")
df_tier_defaults = pd.DataFrame(tier_data)
st.table(df_tier_defaults)

st.caption("Admin Panel v1.3 - Product Tier Defaults + Bespoke Override ✅")
