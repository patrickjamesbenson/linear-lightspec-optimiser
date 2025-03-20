# Linear LightSpec Optimiser v4.8 - Full Testable Streamlit App
# No smoke. No mirrors. Just truth.

import streamlit as st
import pandas as pd
from datetime import datetime

# === CONFIG ===
ADMIN_PASSWORD = "your_secure_password"  # Replace with your secure password
GOOGLE_SHEET_URLS = {
    'LumCAT_Config': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=0',
    'ECG_Config': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=123456',
    'Tier_Rules_Config': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=234567',
    'LED_Chip_Config': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=345678',
    'IES_Normalisation_Map': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=456789',
    'Customer_View_Config': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=567890'
}

# === SESSION STATE ===
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if 'dataset' not in st.session_state:
    st.session_state['dataset'] = None

# === ADMIN LOGIN PANEL ===
with st.sidebar:
    st.subheader("Admin Access")
    if not st.session_state['authenticated']:
        password_input = st.text_input("Enter Admin Password", type="password")
        if password_input == ADMIN_PASSWORD:
            st.session_state['authenticated'] = True
            st.success("Access granted")
        elif password_input:
            st.error("Incorrect password")
    
    if st.session_state['authenticated']:
        st.info("Admin Panel")
        st.markdown("**Google Sheets URLs (Data Sources):**")
        for name, url in GOOGLE_SHEET_URLS.items():
            st.markdown(f"[{name}]({url})")
        if st.button("Reload All Data"):
            st.session_state['dataset'] = None
            st.success("Data cleared. Will reload on refresh.")

# === LOAD DATA FUNCTION ===
def load_google_sheet(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame()

# === LOAD DATA FROM SHEETS ===
@st.cache_data(show_spinner=True)
def load_all_data():
    dataset = {}
    for name, url in GOOGLE_SHEET_URLS.items():
        df = load_google_sheet(url)
        dataset[name] = df
    return dataset

# === LOAD DATA ONCE ===
if st.session_state['dataset'] is None:
    with st.spinner("Loading data from Google Sheets..."):
        st.session_state['dataset'] = load_all_data()

# === MAIN APP ===
st.title("Linear LightSpec Optimiser v4.8")
st.caption("No smoke. No mirrors. Just truth.")

# === CORE DATA DISPLAY ===
st.subheader("📊 Core Dataset Preview")

for name, df in st.session_state['dataset'].items():
    st.markdown(f"### {name}")
    st.dataframe(df.head(10))

# === CUSTOMER LUMINAIRE BUILDER PLACEHOLDER ===
st.subheader("🔨 Customer Luminaire Builder (Coming Next)")
st.info("Select Tiers, Lengths, and Export Options will be here.")

# === FOOTER ===
st.caption(f"Version 4.8 - Powered by Google Sheets - {datetime.now().strftime('%Y-%m-%d')}")
