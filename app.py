import streamlit as st 
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.7 ✅")

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

# === LUMCAT REVERSE LOOKUP ===
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
        lumens_derived = round(float(lumens_code) * 10, 1)

        return {
            "Range": range_code,
            "Option Code": option_code,
            "Diffuser Code": diffuser_code,
            "Wiring Code": wiring_code,
            "Driver Code": driver_code,
            "Lumens (Derived)": lumens_derived,
            "CRI Code": cri_code,
            "CCT Code": cct_code
        }
    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    if matrix_df.empty or parsed_codes is None:
        return None

    matrix_df.columns = matrix_df.columns.str.strip()

    def get_value(df, code_col, desc_col, code):
        match = df.loc[df[code_col] == code]
        return match[desc_col].values[0] if not match.empty else "⚠️ Not Found"

    return {
        'Range': parsed_codes['Range'],
        'Option Description [BS]': get_value(matrix_df, 'Option Code', 'Option Description', parsed_codes['Option Code']),
        'Diffuser Description [A3]': get_value(matrix_df, 'Diffuser / Louvre Code', 'Diffuser / Louvre Description', parsed_codes['Diffuser Code']),
        'Wiring Description [A]': get_value(matrix_df, 'Wiring Code', 'Wiring Description', parsed_codes['Wiring Code']),
        'Driver Description [A1]': get_value(matrix_df, 'Driver Code', 'Driver Description', parsed_codes['Driver Code']),
        'Lumens (Derived) [488]': parsed_codes['Lumens (Derived)'],
        'CRI Description [80]': get_value(matrix_df, 'CRI Code', 'CRI Description', parsed_codes['CRI Code']),
        'CCT Description [30]': get_value(matrix_df, 'CCT/Colour Code', 'CCT/Colour Description', parsed_codes['CCT Code'])
    }

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

    # === LED & BOARD CONFIG DATA ===
    led_board_df = st.session_state['dataset']['LED_and_Board_Config']
    default_led = led_board_df.iloc[0] if not led_board_df.empty else None

    actual_led_current = 0
    max_led_stress = 0
    chip_name = ""
    default_tier = ""
    tm30_code = ""

    if default_led is not None:
        try:
            series_leds = default_led["Series LED's"]
            led_pitch = default_led['LED Pitch (mm)'] / 1000
            actual_led_current = round((input_watts / length_m) * led_pitch, 1)
            max_led_stress = default_led['Max LED Load (mA)']
            chip_name = default_led['Chip Name']
            default_tier = default_led['Default Tier']
            tm30_code = default_led['Internal Code / TM30']
        except Exception as e:
            st.error(f"LED Board Calc Error: {e}")

    with st.expander("📏 Photometric Parameters + Metadata + Base Values", expanded=True):
        # === IES Metadata ===
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # === Photometric Parameters ===
        st.markdown("#### Photometric Parameters")
        photometric_table = [
            {"Param": "A", "Description": "Lamps", "Value": round(photometric_params[0], 1)},
            {"Param": "B", "Description": "Lumens/Lamp", "Value": round(photometric_params[1], 1)},
            {"Param": "C", "Description": "Candela Mult.", "Value": round(photometric_params[2], 1)},
            {"Param": "D", "Description": "Vert Angles", "Value": round(photometric_params[3], 1)},
            {"Param": "E", "Description": "Horiz Angles", "Value": round(photometric_params[4], 1)},
            {"Param": "F", "Description": "Photometric Type", "Value": round(photometric_params[5], 1)},
            {"Param": "G", "Description": "Units Type", "Value": round(photometric_params[6], 1)},
            {"Param": "H", "Description": "Width (m)", "Value": round(photometric_params[7], 1)},
            {"Param": "I", "Description": "Length (m)", "Value": round(photometric_params[8], 1)},
            {"Param": "J", "Description": "Height (m)", "Value": round(photometric_params[9], 1)},
            {"Param": "K", "Description": "Ballast Factor", "Value": round(photometric_params[10], 1)},
            {"Param": "L", "Description": "Future Use", "Value": round(photometric_params[11], 1)},
            {"Param": "M", "Description": "Input Watts [F]", "Value": round(photometric_params[12], 1)}
        ]
        st.table(pd.DataFrame(photometric_table))

        # === Base Values ===
        st.markdown("#### Base Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Default Tier", "LED Base": default_tier},
            {"Description": "Chip Name", "LED Base": chip_name},
            {"Description": "Max LED Load (mA)", "LED Base": max_led_stress},
            {"Description": "Actual LED Current (mA)", "LED Base": actual_led_current},
            {"Description": "Internal Code / TM30", "LED Base": tm30_code}
        ]
        st.table(pd.DataFrame(base_values))

    # === LUMCAT REVERSE LOOKUP ===
    with st.expander("🔎 LumCAT Reverse Lookup (Matrix)", expanded=False):
        lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
        lumcat_from_meta = meta_dict.get("[LUMCAT]", "")

        lumcat_input = st.text_input("Enter LumCAT Code", value=lumcat_from_meta)

        if lumcat_input:
            parsed_codes = parse_lumcat(lumcat_input)
            if parsed_codes:
                lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
                if lumcat_desc:
                    st.markdown("#### Reverse Lookup Results")
                    st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === FOOTER ===
st.caption("Version 4.7 Clean ✅ - Dataset Upload + Unified Base Info + LumCAT Reverse Lookup")
