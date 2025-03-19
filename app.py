import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.7 Clean ✅")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}

# === DEFAULT DATASET LOAD ===
default_excel_path = 'Linear_Lightspec_Data.xlsx'
if os.path.exists(default_excel_path):
    workbook = pd.ExcelFile(default_excel_path)
    st.session_state['dataset'] = {
        'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
        'LED_and_Board_Config': pd.read_excel(workbook, 'LED_and_Board_Config'),
        'ECG_Config': pd.read_excel(workbook, 'ECG_Config')
    }
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")

    uploaded_excel = st.file_uploader("Upload Dataset Excel", type=["xlsx"])
    if uploaded_excel:
        workbook = pd.ExcelFile(uploaded_excel)
        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
            'LED_and_Board_Config': pd.read_excel(workbook, 'LED_and_Board_Config'),
            'ECG_Config': pd.read_excel(workbook, 'ECG_Config')
        }

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
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

# === LUMCAT PARSE FUNCTIONS (UPDATED) ===
def parse_lumcat(lumcat_code):
    try:
        range_code, rest = lumcat_code.split('-')

        option_code = rest[0:2]
        diffuser_code = rest[2:4]
        wiring_code = rest[4]
        driver_code = rest[5:7]
        lumens_code = rest[7:10]
        cri_code = rest[10:12]
        cct_code = rest[12:14]

        # Multiply by 10 for display
        lumens_derived_display = round(float(lumens_code) * 10, 1)

        return {
            "Range": range_code,
            "Option Code": option_code,
            "Diffuser Code": diffuser_code,
            "Wiring Code": wiring_code,
            "Driver Code": driver_code,
            "Lumens Derived Display": lumens_derived_display,
            "CRI Code": cri_code,
            "CCT Code": cct_code
        }

    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    if matrix_df.empty or parsed_codes is None:
        return None

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
    result['Lumens (Display Only)'] = f"{parsed_codes['Lumens Derived Display']} lm"  # Display only, not for calculations
    result['CRI Description'] = cri_match['CRI Description'].values[0] if not cri_match.empty else "⚠️ Not Found"
    result['CCT Description'] = cct_match['CCT/Colour Description'].values[0] if not cct_match.empty else "⚠️ Not Found"

    return result

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    with st.expander("📏 Parameters + Metadata + Derived Values", expanded=False):
        # === IES Metadata ===
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # === IES Parameters ===
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

        # === IES Derived Values ===
        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Default Tier / Chip", "LED Base": f"{default_led['Default Tier']} / {default_led['Chip Name']}"},
            {"Description": "Max LED Load (mA)", "LED Base": f"{default_led['Max LED Load (mA)']}"},
            {"Description": "Actual LED Current (mA)", "LED Base": f"{actual_led_current}"},
            {"Description": "TM30 Code", "LED Base": f"{default_led['Internal Code / TM30']}"}
        ]
        st.table(pd.DataFrame(base_values))

# === LUMCAT REVERSE LOOKUP ===
def parse_lumcat(lumcat_code):
    try:
        range_code, rest = lumcat_code.split('-')
        return {
            "Range": range_code,
            "Option Code": rest[0:2],
            "Diffuser Code": rest[2:4],
            "Wiring Code": rest[4],
            "Driver Code": rest[5:7],
            "Lumens (Derived)": round(float(rest[7:10]) * 10, 1),
            "CRI Code": rest[10:12],
            "CCT Code": rest[12:14]
        }
    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    matrix_df.columns = matrix_df.columns.str.strip()

    def get_value(df, code_col, desc_col, code):
        match = df.loc[df[code_col] == code]
        return match[desc_col].values[0] if not match.empty else "⚠️ Not Found"

    return {
        'Range': parsed_codes['Range'],
        'Option Description': get_value(matrix_df, 'Option Code', 'Option Description', parsed_codes['Option Code']),
        'Diffuser Description': get_value(matrix_df, 'Diffuser / Louvre Code', 'Diffuser / Louvre Description', parsed_codes['Diffuser Code']),
        'Wiring Description': get_value(matrix_df, 'Wiring Code', 'Wiring Description', parsed_codes['Wiring Code']),
        'Driver Description': get_value(matrix_df, 'Driver Code', 'Driver Description', parsed_codes['Driver Code']),
        'Lumens (Derived)': parsed_codes['Lumens (Derived)'],
        'CRI Description': get_value(matrix_df, 'CRI Code', 'CRI Description', parsed_codes['CRI Code']),
        'CCT Description': get_value(matrix_df, 'CCT/Colour Code', 'CCT/Colour Description', parsed_codes['CCT Code'])
    }

# === LUMCAT EXPANDER ===
with st.expander("🔎 LumCAT Reverse Lookup (Matrix)", expanded=False):
    lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
    lumcat_from_meta = meta_dict.get("[LUMCAT]", "")

    lumcat_input = st.text_input("Enter LumCAT Code", value=lumcat_from_meta)

    if lumcat_input:
        parsed_codes = parse_lumcat(lumcat_input)
        if parsed_codes:
            lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
            if lumcat_desc:
                st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === FOOTER ===
st.caption("Version 4.7 Clean ✅ - Unified Base Info + LumCAT Reverse Lookup + Confirmed Dataset")
