import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v4.8")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === DEFAULT DATASET LOAD ===
default_excel_path = 'Linear_Data.xlsx'
if os.path.exists(default_excel_path):
    workbook = pd.ExcelFile(default_excel_path)
    st.session_state['dataset'] = {
        'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
        'LED_and_Board_Config': pd.read_excel(workbook, 'LED_Chip_Config'),
        'ECG_Config': pd.read_excel(workbook, 'ECG_Config'),
        'Tier_Rules_Config': pd.read_excel(workbook, 'Tier_Rules_Config')
    }
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Data Upload")

    uploaded_excel = st.file_uploader("Upload Data Excel", type=["xlsx"])
    if uploaded_excel:
        workbook = pd.ExcelFile(uploaded_excel)
        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
            'LED_and_Board_Config': pd.read_excel(workbook, 'LED_Chip_Config'),
            'ECG_Config': pd.read_excel(workbook, 'ECG_Config'),
            'Tier_Rules_Config': pd.read_excel(workbook, 'Tier_Rules_Config')
        }

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === TIER LOOKUP FUNCTION ===
def get_tier_values(tier_name):
    tier_rules = st.session_state['dataset']['Tier_Rules_Config']
    led_chip_config = st.session_state['dataset']['LED_and_Board_Config']

    tier_row_rules = tier_rules[tier_rules['Tier'] == tier_name].iloc[0]
    led_chip_row = led_chip_config[led_chip_config['Tier'] == tier_name].iloc[0]

    return {
        'Default Tier': tier_row_rules['Default'],
        'Chip Name': led_chip_row['Chip Name'],
        'Max LED Load (mA)': led_chip_row['Max LED Load (mA)'],
        'Internal Code / TM30': led_chip_row['Internal Code / TM30'],
        'Board Segment LED Pitch': tier_row_rules['Board Segment LED Pitch (mm)'],
        'LED Strip Voltage': led_chip_row['LED Strip Voltage (SELV)']
    }

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content']
    )

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    # Default lookup for Core Tier
    tier_values = get_tier_values("Core")

    actual_led_current_ma = round((input_watts / tier_values['LED Strip Voltage']) / tier_values['Board Segment LED Pitch'] * 1000, 1)

    with st.expander("📏 Parameters + Metadata + Derived Values", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("#### IES Parameters")
        photometric_table = [
            {"Description": "Lamps", "Value": f"{photometric_params[0]}"},
            {"Description": "Lumens/Lamp", "Value": f"{photometric_params[1]}"},
            {"Description": "Candela Mult.", "Value": f"{photometric_params[2]}"},
            {"Description": "Vert Angles", "Value": f"{photometric_params[3]}"},
            {"Description": "Horiz Angles", "Value": f"{photometric_params[4]}"},
            {"Description": "Photometric Type", "Value": f"{photometric_params[5]}"},
            {"Description": "Units Type", "Value": f"{photometric_params[6]}"},
            {"Description": "Width (m)", "Value": f"{photometric_params[7]}"},
            {"Description": "Length (m)", "Value": f"{photometric_params[8]}"},
            {"Description": "Height (m)", "Value": f"{photometric_params[9]}"},
            {"Description": "Ballast Factor", "Value": f"{photometric_params[10]}"},
            {"Description": "Future Use", "Value": f"{photometric_params[11]}"},
            {"Description": "Input Watts [F]", "Value": f"{photometric_params[12]}"}
        ]
        st.table(pd.DataFrame(photometric_table))

        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Default Tier / Chip", "LED Base": f"{tier_values['Default Tier']} / {tier_values['Chip Name']}"},
            {"Description": "Max LED Load (mA)", "LED Base": f"{tier_values['Max LED Load (mA)']:.1f}"},
            {"Description": "LED Pitch (mm)", "LED Base": f"{tier_values['Board Segment LED Pitch']:.1f}"},
            {"Description": "Actual LED Current (mA)", "LED Base": f"{actual_led_current_ma:.1f}"},
            {"Description": "TM30 Code", "LED Base": f"{tier_values['Internal Code / TM30']}"}
        ]
        st.table(pd.DataFrame(base_values))

        st.markdown("#### 🔎 LumCAT Lookup")
        lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
        lumcat_from_meta = meta_dict.get("[LUMCAT]", "")

        lumcat_input = st.text_input("Enter LumCAT Code", value=lumcat_from_meta)

        if lumcat_input:
            parsed_codes = parse_lumcat(lumcat_input)
            if parsed_codes:
                lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
                if lumcat_desc:
                    st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === CUSTOMER LUMINAIRE BUILDER ===
st.subheader("🔨 Customer Luminaire Builder")

with st.form("luminaire_entry_form"):
    luminaire_name = st.text_input("Luminaire Name")
    tier_selection = st.selectbox("Select Tier", ["Core", "Professional", "Advanced"])
    length_input = st.number_input("Enter Required Length (mm)", min_value=280, step=10)
    notes_input = st.text_input("Notes (e.g., Room Name, Mounting Type)")
    submitted = st.form_submit_button("Add to Table")

    if submitted:
        new_entry = {
            'Luminaire Name': luminaire_name,
            'Tier': tier_selection,
            'Selected Length (mm)': length_input,
            'Notes': notes_input,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state['customer_entries'].append(new_entry)
        st.success("Luminaire added to table.")

st.markdown("### Current Luminaire Selections")
if st.session_state['customer_entries']:
    customer_df = pd.DataFrame(st.session_state['customer_entries'])
    st.dataframe(customer_df)

    csv = customer_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"luminaire_selections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.info("No luminaires added yet.")

# === FOOTER ===
st.caption("Version 4.8 - Unified Base Info + LumCAT Lookup + Customer Builder")
