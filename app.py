import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.8 Clean ✅")

# === SESSION STATE INITIALIZATION ===
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = None

# === DEFAULT DATASET AUTO-LOAD ===
default_dataset_path = "./Linear_Lightspec_Data.xlsx"
if os.path.exists(default_dataset_path):
    try:
        xl_data = pd.ExcelFile(default_dataset_path)
        matrix_lookup = pd.read_excel(xl_data, sheet_name='Matrix_Lookup')
        led_chips = pd.read_excel(xl_data, sheet_name='LED_Chips').dropna(axis=1, how='all')
        ecg_config = pd.read_excel(xl_data, sheet_name='ECG_Config').dropna(axis=1, how='all')
        st.session_state['dataset'] = {
            'Matrix_Lookup': matrix_lookup,
            'LED_Chips': led_chips,
            'ECG_Config': ecg_config
        }
        st.success("✅ Default Dataset Loaded Successfully!")
    except Exception as e:
        st.error(f"Error loading default dataset: {e}")
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")

    dataset_file = st.file_uploader("Upload Dataset Excel (Recommended: Linear_Lightspec_Data.xlsx)", type=["xlsx"])
    if dataset_file:
        try:
            xl_data = pd.ExcelFile(dataset_file)
            matrix_lookup = pd.read_excel(xl_data, sheet_name='Matrix_Lookup')
            led_chips = pd.read_excel(xl_data, sheet_name='LED_Chips').dropna(axis=1, how='all')
            ecg_config = pd.read_excel(xl_data, sheet_name='ECG_Config').dropna(axis=1, how='all')

            st.session_state['dataset'] = {
                'Matrix_Lookup': matrix_lookup,
                'LED_Chips': led_chips,
                'ECG_Config': ecg_config
            }
            st.success("✅ New Dataset Loaded Successfully!")
        except Exception as e:
            st.error(f"Error loading Excel: {e}")

# === CHECK IF DATA LOADED ===
if not st.session_state['dataset']:
    st.stop()

# === DATA REFERENCES ===
matrix_lookup = st.session_state['dataset']['Matrix_Lookup']
led_chips = st.session_state['dataset']['LED_Chips']
ecg_config = st.session_state['dataset']['ECG_Config']

# === LED CHIP SELECTION ===
st.subheader("🔧 LED Chip Selection")

if not led_chips.empty:
    chip_names = led_chips['Chip Name'].tolist()
    selected_chip = st.selectbox("Select LED Chip", chip_names)

    chip_data = led_chips[led_chips['Chip Name'] == selected_chip].iloc[0]

    st.markdown("#### LED Chip Details")
    st.markdown(f"- **Chip Name [Z1]:** {chip_data['Chip Name']}")
    st.markdown(f"- **Internal Code [Z2]:** {chip_data['Internal Code']}")
    st.markdown(f"- **Max LED Stress [Z3] (mA):** {chip_data['Max LED Stress (mA)']}")
    st.markdown(f"- **Dimensions [Z4] (mm):** {chip_data['Chip Length (mm)']} x {chip_data['Chip Width (mm)']}")
    st.markdown(f"- **Bound Row Spacing [Z5] (mm):** {chip_data['Bound Row Spacing (mm)']}")
    st.markdown(f"- **Placement Direction [Z6]:** {chip_data['Placement Direction (Length/Width)']}")
    st.markdown(f"- **Default Tier [Z7]:** {chip_data['Default Tier']}")
    st.markdown(f"- **Status [Z8]:** {chip_data['Status']}")
    st.markdown(f"- **Comment [Z9]:** {chip_data['Comment']}")

else:
    st.warning("⚠️ No LED chips found in the dataset.")

# === ECG SELECTION ===
st.subheader("⚡ ECG Selection")

if not ecg_config.empty:
    ecg_names = ecg_config['ECG Model Name'].tolist()
    selected_ecg = st.selectbox("Select ECG Model", ecg_names)

    ecg_data = ecg_config[ecg_config['ECG Model Name'] == selected_ecg].iloc[0]

    st.markdown("#### ECG Details")
    st.markdown(f"- **ECG Model [Y1]:** {ecg_data['ECG Model Name']}")
    st.markdown(f"- **Internal Code [Y2]:** {ecg_data['Internal Code']}")
    st.markdown(f"- **Max Output [Y3] (W):** {ecg_data['Max Output (W)']}")
    st.markdown(f"- **Engineering Safety Factor [Y4]:** {ecg_data['Eng Safety Design Factor']}%")
    st.markdown(f"- **Stress Limits (Core/Pro/Adv/Custom) [Y5]:** {ecg_data['Stress limit Core']}% / {ecg_data['Stress limit Professional']}% / {ecg_data['Stress limit Advanced']}% / {ecg_data['Stress limit Custom']}%")
    st.markdown(f"- **Default Tier [Y6]:** {ecg_data['Default Tier']}")
    st.markdown(f"- **Status [Y7]:** {ecg_data['Status']}")
    st.markdown(f"- **Comment [Y8]:** {ecg_data['Comment']}")

else:
    st.warning("⚠️ No ECG config found in the dataset.")

# === FOOTER ===
st.caption("Version 4.8 - LED & ECG Lookup from Dataset ✅")
