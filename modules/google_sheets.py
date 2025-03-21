import streamlit as st
import pandas as pd

GOOGLE_SHEET_ID = '19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs'

def load_google_sheet_data() -> None:
    try:
        lumcat_url = f'https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=LumCAT_Config'
        build_data_url = f'https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Build_Data'
        view_config_url = f'https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Customer_View_Config'

        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_csv(lumcat_url),
            'Build_Data': pd.read_csv(build_data_url),
            'Customer_View_Config': pd.read_csv(view_config_url)
        }
        st.success("✅ Successfully loaded Google Sheets data")
    except Exception as e:
        st.error(f"❌ Failed to load dataset: {e}")

def get_tooltip(field: str) -> str:
    tooltips_df = st.session_state['dataset'].get('Customer_View_Config')
    if tooltips_df is not None:
        if 'Field' in tooltips_df.columns and 'Tooltip' in tooltips_df.columns:
            match = tooltips_df[tooltips_df['Field'].str.strip() == field.strip()]
            if not match.empty:
                return match['Tooltip'].values[0]
    return ""
