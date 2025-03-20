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
def load_dataset():
    default_excel_path = 'Linear_Data.xlsx'
    if os.path.exists(default_excel_path):
        workbook = pd.ExcelFile(default_excel_path)
        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
            'LED_Chip_Config': pd.read_excel(workbook, 'LED_Chip_Config'),
            'ECG_Config': pd.read_excel(workbook, 'ECG_Config'),
            'Tier_Rules_Config': pd.read_excel(workbook, 'Tier_Rules_Config')
        }
    else:
        st.warning("⚠️ Default dataset not found! Please upload manually.")

load_dataset()

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Data Upload")

    uploaded_excel = st.file_uploader("Upload Data Excel", type=["xlsx"])
    if uploaded_excel:
        workbook = pd.ExcelFile(uploaded_excel)
        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
            'LED_Chip_Config': pd.read_excel(workbook, 'LED_Chip_Config'),
            'ECG_Config': pd.read_excel(workbook, 'ECG_Config'),
            'Tier_Rules_Config': pd.read_excel(workbook, 'Tier_Rules_Config')
        }

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === PARSE FUNCTIONS ===
def parse_ies_file(file_content):
    lines = file_content.splitlines()
    header_lines, data_lines = [], []
    reading_data = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TILT"):
            reading_data = True
        elif not reading_data:
            header_lines.append(stripped)
        else:
            data_lines.append(stripped)

    photometric_raw = " ".join(data_lines[:2]).split()
    photometric_params = [float(x) if '.' in x or 'e' in x.lower() else int(x) for x in photometric_raw]
    n_vert = int(photometric_params[3])
    n_horz = int(photometric_params[4])

    remaining_data = " ".join(data_lines[2:]).split()
    vertical_angles = [float(x) for x in remaining_data[:n_vert]]
    horizontal_angles = [float(x) for x in remaining_data[n_vert:n_vert + n_horz]]

    candela_values = remaining_data[n_vert + n_horz:]
    candela_matrix = []
    idx = 0
    for _ in range(n_horz):
        row = [float(candela_values[idx + i]) for i in range(n_vert)]
        candela_matrix.append(row)
        idx += n_vert

    return header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix

def corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix, symmetry_factor=4):
    vert_rad = np.radians(vertical_angles)
    delta_vert = np.diff(vert_rad)
    delta_vert = np.append(delta_vert, delta_vert[-1])

    symmetry_range_rad = np.radians(horizontal_angles[-1] - horizontal_angles[0])
    num_horz_segments = len(horizontal_angles)
    uniform_delta_horz = symmetry_range_rad / num_horz_segments

    total_flux = 0.0
    for h_idx in range(num_horz_segments):
        candela_row = candela_matrix[h_idx]
        for v_idx, cd in enumerate(candela_row):
            theta = vert_rad[v_idx]
            d_theta = delta_vert[v_idx]
            flux = cd * np.sin(theta) * d_theta * uniform_delta_horz
            total_flux += flux

    return round(total_flux * symmetry_factor, 1)

# === TIER LOOKUP FUNCTION ===
def get_tier_values():
    tier_rules = st.session_state['dataset']['Tier_Rules_Config']
    led_chip_config = st.session_state['dataset']['LED_Chip_Config']

    tier_row_rules = tier_rules[tier_rules['Default'].astype(str).str.lower() == 'yes']
    led_chip_row = led_chip_config[led_chip_config['Default'].astype(str).str.lower() == 'yes']

    if tier_row_rules.empty or led_chip_row.empty:
        st.error("Default row not found in Tier_Rules_Config or LED_Chip_Config")
        return {}

    tier_row_rules = tier_row_rules.iloc[0]
    led_chip_row = led_chip_row.iloc[0]

    return {
        'Default Tier': tier_row_rules['Tier'],
        'Chip Name': led_chip_row['Chip_Name'],
        'Max LED Load (mA)': led_chip_row['Max LED Load (mA)'],
        'Internal Code / TM30': led_chip_row['TM30-report ref.'],
        'Board Segment LED Pitch': tier_row_rules['Series LED Pitch (mm)'],
        'LED Strip Voltage': led_chip_row['Vf (Volts)']
    }

# === LUMCAT PARSE FUNCTIONS ===
def parse_lumcat(lumcat_code):
    try:
        range_code, rest = lumcat_code.split('-')

        parsed = {
            "Range": range_code,
            "Option Code": rest[0:2],
            "Diffuser Code": rest[2:4],
            "Wiring Code": rest[4],
            "Driver Code": rest[5:7],
            "Lumens Code": rest[7:10],
            "CRI Code": rest[10:12],
            "CCT Code": rest[12:14],
        }

        parsed['Lumens Derived Display'] = round(float(parsed["Lumens Code"]) * 10, 1)

        return parsed

    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    if matrix_df.empty or parsed_codes is None:
        return None

    matrix_df.columns = matrix_df.columns.str.strip()
    matrix_df['CRI Code'] = matrix_df['CRI Code'].astype(str).str.strip()
    matrix_df['CCT/Colour Code'] = matrix_df['CCT/Colour Code'].astype(str).str.strip()

    parsed_codes['CRI Code'] = str(parsed_codes['CRI Code']).strip()
    parsed_codes['CCT Code'] = str(parsed_codes['CCT Code']).strip()

    result = {}
    result['Range'] = parsed_codes['Range']

    option_match = matrix_df.loc[matrix_df['Option Code'] == parsed_codes['Option Code']]
    diffuser_match = matrix_df.loc[matrix_df['Diffuser / Louvre Code'] == parsed_codes['Diffuser Code']]
    wiring_match = matrix_df.loc[matrix_df['Wiring Code'] == parsed_codes['Wiring Code']]
    driver_match = matrix_df.loc[matrix_df['Driver Code'] == parsed_codes['Driver Code']]
    cri_match = matrix_df.loc[matrix_df['CRI Code'] == parsed_codes['CRI Code']]
    cct_match = matrix_df.loc[matrix_df['CCT/Colour Code'] == parsed_codes['CCT Code']]

    result['Option Description'] = option_match['Option Description'].values[0] if not option_match.empty else "⚠️ Not Found"
    result['Diffuser Description'] = diffuser_match['Diffuser / Louvre Description'].values[0] if not diffuser_match.empty else "⚠️ Not Found"
    result['Wiring Description'] = wiring_match['Wiring Description'].values[0] if not wiring_match.empty else "⚠️ Not Found"
    result['Driver Description'] = driver_match['Driver Description'].values[0] if not driver_match.empty else "⚠️ Not Found"
    result['Lumens (Display Only)'] = f"{parsed_codes['Lumens Derived Display']} lm"
    result['CRI Description'] = cri_match['CRI Description'].values[0] if not cri_match.empty else "⚠️ Not Found"
    result['CCT Description'] = cct_match['CCT/Colour Description'].values[0] if not cct_match.empty else "⚠️ Not Found"

    return result

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content']
    )

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    tier_values = get_tier_values()

    if tier_values:
        actual_led_current_ma = round(
            (input_watts / tier_values['LED Strip Voltage']) /
            tier_values['Board Segment LED Pitch'] * 1000, 1
        )

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
