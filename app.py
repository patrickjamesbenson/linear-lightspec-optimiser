import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.7 Clean")

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

# === DISPLAY PARSED DATA ===
st.header("📊 Dataset Overview")

st.subheader("🔎 Matrix Lookup Data (First 5 Rows)")
if not matrix_lookup.empty:
    st.dataframe(matrix_lookup.head())
else:
    st.warning("⚠️ No Matrix_Lookup data found in the dataset.")

st.subheader("🔧 LED Chip Data (First 5 Rows)")
if not led_chips.empty:
    st.dataframe(led_chips.head())
else:
    st.warning("⚠️ No LED_Chips data found in the dataset.")

st.subheader("⚡ ECG Configuration Data (First 5 Rows)")
if not ecg_config.empty:
    st.dataframe(ecg_config.head())
else:
    st.warning("⚠️ No ECG_Config data found in the dataset.")

# === FOOTER ===
st.caption("Version 4.7 Clean - Dataset Upload + Unified Base Info ✅")
