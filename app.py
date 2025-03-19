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
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

# === DEFAULT DATASET AUTO-LOAD ===
default_dataset_path = "Linear_Lightspec_Data.xlsx"

def load_dataset_from_excel(file_path):
    try:
        xl = pd.ExcelFile(file_path)
        data = {
            "LumCAT_Matrix": xl.parse("LumCAT_Matrix"),
            "LED_and_Board_Config": xl.parse("LED_and_Board_Config"),
            "ECG_Config": xl.parse("ECG_Config")
        }
        return data
    except Exception as e:
        st.error(f"❌ Error loading Excel: {e}")
        return {}

if os.path.exists(default_dataset_path):
    st.session_state['dataset'] = load_dataset_from_excel(default_dataset_path)
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")
    uploaded_excel = st.file_uploader("Upload Dataset Excel (Recommended: Linear_Lightspec_Data.xlsx)", type=["xlsx"])
    if uploaded_excel:
        st.session_state['dataset'] = load_dataset_from_excel(uploaded_excel)
        st.success("✅ Dataset loaded successfully!")

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    st.success(f"{uploaded_file.name} uploaded!")

# === PARSE IES FUNCTIONS ===
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

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    with st.expander("📏 Photometric Parameters + Metadata + Base Values", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        photometric_data = [
            {"Param [A]": "Lamps", "Value": f"{photometric_params[0]}"},
            {"Param [B]": "Lumens/Lamp", "Value": f"{photometric_params[1]}"},
            {"Param [C]": "Candela Mult.", "Value": f"{photometric_params[2]}"},
            {"Param [D]": "Vert Angles", "Value": f"{photometric_params[3]}"},
            {"Param [E]": "Horiz Angles", "Value": f"{photometric_params[4]}"},
            {"Param [F]": "Photometric Type", "Value": f"{photometric_params[5]}"},
            {"Param [G]": "Units Type", "Value": f"{photometric_params[6]}"},
            {"Param [H]": "Width (m)", "Value": f"{photometric_params[7]}"},
            {"Param [I]": "Length (m)", "Value": f"{photometric_params[8]}"},
            {"Param [J]": "Height (m)", "Value": f"{photometric_params[9]}"},
            {"Param [K]": "Ballast Factor", "Value": f"{photometric_params[10]}"},
            {"Param [L]": "Future Use", "Value": f"{photometric_params[11]}"},
            {"Param [M]": "Input Watts [F]", "Value": f"{photometric_params[12]}"}
        ]
        st.markdown("#### Photometric Parameters")
        st.table(pd.DataFrame(photometric_data))

        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Base LED Chip", "LED Base": "G1 (Gen1 Spec: TM30 Report XXX)"},
            {"Description": "Base Design", "LED Base": "6S/4P/14.4W/280mm/400mA/G1/DR12w"}
        ]
        st.markdown("#### Base Values")
        st.table(pd.DataFrame(base_values))

    # === LumCAT Reverse Lookup ===
    st.markdown("🔎 LumCAT Reverse Lookup (Matrix)")
    lumcat_code = meta_dict.get("[LUMCAT]", "")

    def parse_lumcat(code):
        try:
            range_code, rest = code.split('-')
            return {
                "Range": range_code,
                "Option Code": rest[0:2],
                "Diffuser Code": rest[2:4],
                "Wiring Code": rest[4],
                "Driver Code": rest[5:7],
                "Lumens Derived": round(float(rest[7:10]) * 10, 3),
                "CRI Code": rest[10:12],
                "CCT Code": rest[12:14]
            }
        except:
            return None

    def lookup_lumcat_descriptions(parsed, df):
        if not parsed or df.empty:
            return None
        desc = {
            "Range": parsed['Range'],
            "Option Description": df.loc[df['Option Code'] == parsed['Option Code'], 'Option Description'].values[0] if not df[df['Option Code'] == parsed['Option Code']].empty else "⚠️ Not Found",
            "Diffuser Description": df.loc[df['Diffuser / Louvre Code'] == parsed['Diffuser Code'], 'Diffuser / Louvre Description'].values[0] if not df[df['Diffuser / Louvre Code'] == parsed['Diffuser Code']].empty else "⚠️ Not Found",
            "Wiring Description": df.loc[df['Wiring Code'] == parsed['Wiring Code'], 'Wiring Description'].values[0] if not df[df['Wiring Code'] == parsed['Wiring Code']].empty else "⚠️ Not Found",
            "Driver Description": df.loc[df['Driver Code'] == parsed['Driver Code'], 'Driver Description'].values[0] if not df[df['Driver Code'] == parsed['Driver Code']].empty else "⚠️ Not Found",
            "Lumens (Derived)": f"{parsed['Lumens Derived']} lm",
            "CRI Description": df.loc[df['CRI Code'] == parsed['CRI Code'], 'CRI Description'].values[0] if not df[df['CRI Code'] == parsed['CRI Code']].empty else "⚠️ Not Found",
            "CCT Description": df.loc[df['CCT/Colour Code'] == parsed['CCT Code'], 'CCT/Colour Description'].values[0] if not df[df['CCT/Colour Code'] == parsed['CCT Code']].empty else "⚠️ Not Found"
        }
        return desc

    parsed_codes = parse_lumcat(lumcat_code)
    lumcat_desc = lookup_lumcat_descriptions(parsed_codes, st.session_state['dataset']['LumCAT_Matrix'])

    if lumcat_desc:
        st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))
    else:
        st.info("Please upload a valid IES file with LumCAT Code.")

else:
    st.info("📄 Upload your IES file to proceed.")

# === FOOTER ===
st.caption("Version 4.7 Clean - Dataset Excel + Unified Base Info ✅")
