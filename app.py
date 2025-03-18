import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.8 Alpha")

# === SESSION STATE INITIALIZATION ===
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []

# === LOAD DATASET ===
default_dataset_path = 'Linear_Lightspec_Data.xlsx'

def load_dataset(path):
    try:
        dataset = pd.read_excel(path, sheet_name=None)
        st.session_state['dataset'] = dataset
        st.success(f"✅ Loaded dataset from {path}")
    except Exception as e:
        st.error(f"❌ Error loading Excel: {e}")

# === AUTOLOAD DATASET ON STARTUP ===
if os.path.exists(default_dataset_path):
    load_dataset(default_dataset_path)
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR: UPLOAD OPTION ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")
    dataset_file = st.file_uploader("Upload Dataset Excel (Recommended: Linear_Lightspec_Data.xlsx)", type=["xlsx"])
    if dataset_file:
        try:
            dataset = pd.read_excel(dataset_file, sheet_name=None)
            st.session_state['dataset'] = dataset
            st.success(f"✅ Dataset uploaded: {dataset_file.name}")
        except Exception as e:
            st.error(f"❌ Failed to load dataset: {e}")

# === ACCESS PARSED SHEETS ===
matrix_lookup = st.session_state['dataset'].get('Matrix_Lookup', pd.DataFrame())
led_chips = st.session_state['dataset'].get('LED_Chips', pd.DataFrame())
ecg_config = st.session_state['dataset'].get('ECG_Config', pd.DataFrame())

# === MAIN DISPLAY ===
st.header("📊 Dataset Overview")

# === LED CHIP SELECTION ===
st.subheader("🔧 LED Chip Selection")
if not led_chips.empty:
    chip_names = led_chips['Chip Name'].tolist()
    selected_chip = st.selectbox("Select LED Chip", chip_names)

    chip_data = led_chips[led_chips['Chip Name'] == selected_chip].iloc[0]

    st.markdown("#### LED Chip Details")
    st.markdown(f"- **Chip Name:** {chip_data['Chip Name']} [Z1]")
    st.markdown(f"- **Lumen Output (lm):** {chip_data['Lumen Output']} lm [Z2]")
    st.markdown(f"- **Max Current (mA):** {chip_data['Max Current (mA)']} mA [Z3]")
    st.markdown(f"- **Dimensions (mm):** {chip_data['Length (mm)']} x {chip_data['Width (mm)']} [Z4]")
    st.markdown(f"- **Engineering Safety Factor:** {chip_data['Engineering Safety Factor (%)']}% [Z5]")
    
    st.markdown("**Stress Levels (mA / % of Max):**")
    st.markdown(f"- Low: {chip_data['Stress Level Low (%)']}% ➜ {round(chip_data['Max Current (mA)'] * chip_data['Stress Level Low (%)'] / 100, 1)} mA [Z6]")
    st.markdown(f"- Med: {chip_data['Stress Level Med (%)']}% ➜ {round(chip_data['Max Current (mA)'] * chip_data['Stress Level Med (%)'] / 100, 1)} mA [Z7]")
    st.markdown(f"- High: {chip_data['Stress Level High (%)']}% ➜ {round(chip_data['Max Current (mA)'] * chip_data['Stress Level High (%)'] / 100, 1)} mA [Z8]")

else:
    st.warning("⚠️ No LED Chip data found in the dataset.")

# === ECG SELECTION ===
st.subheader("⚡ ECG Selection")
if not ecg_config.empty:
    ecg_names = ecg_config['ECG Model Name'].tolist()
    selected_ecg = st.selectbox("Select ECG Model", ecg_names)

    ecg_data = ecg_config[ecg_config['ECG Model Name'] == selected_ecg].iloc[0]

    st.markdown("#### ECG Details")
    st.markdown(f"- **ECG Model Name:** {ecg_data['ECG Model Name']} [E1]")
    st.markdown(f"- **Max Power (W):** {ecg_data['Max Power (W)']} W [E2]")
    st.markdown(f"- **Efficiency (%):** {ecg_data['Efficiency (%)']}% [E3]")
    st.markdown(f"- **Engineering Safety Factor:** {ecg_data['Engineering Safety Factor (%)']}% [E4]")

    st.markdown("**Stress Levels (% of Max Power):**")
    st.markdown(f"- Low: {ecg_data['Stress Level Low (%)']}% ➜ {round(ecg_data['Max Power (W)'] * ecg_data['Stress Level Low (%)'] / 100, 1)} W [E5]")
    st.markdown(f"- Med: {ecg_data['Stress Level Med (%)']}% ➜ {round(ecg_data['Max Power (W)'] * ecg_data['Stress Level Med (%)'] / 100, 1)} W [E6]")
    st.markdown(f"- High: {ecg_data['Stress Level High (%)']}% ➜ {round(ecg_data['Max Power (W)'] * ecg_data['Stress Level High (%)'] / 100, 1)} W [E7]")

else:
    st.warning("⚠️ No ECG Config data found in the dataset.")

# === FOOTER ===
st.caption("Version 4.8 Alpha - LED + ECG Selections + Alpha Indicators ✅")
