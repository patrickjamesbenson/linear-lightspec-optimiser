import streamlit as st
import pandas as pd
import numpy as np
import time
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()

# === SUCCESS BANNER STATE ===
if 'show_success' not in st.session_state:
    st.session_state['show_success'] = False
    st.session_state['success_time'] = 0

# === DEFAULT MATRIX AUTO-LOAD ===
default_matrix_path = "Matrix Headers.csv"
if os.path.exists(default_matrix_path):
    st.session_state['matrix_lookup'] = pd.read_csv(default_matrix_path)
    st.session_state['show_success'] = True
    st.session_state['success_time'] = time.time()
else:
    st.warning("⚠️ Default matrix file not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Matrix Upload / Download")

    matrix_file = st.file_uploader("Upload Matrix CSV (Optional)", type=["csv"])
    if matrix_file:
        df_new_matrix = pd.read_csv(matrix_file)
        required_columns = [
            'Option Code', 'Option Description',
            'Diffuser / Louvre Code', 'Diffuser / Louvre Description',
            'Driver Code', 'Wiring Code', 'Wiring Description',
            'Driver Description', 'Dimensions Code', 'Dimensions Description',
            'CRI Code', 'CRI Description', 'CCT/Colour Code', 'CCT/Colour Description'
        ]
        if all(col in df_new_matrix.columns for col in required_columns):
            st.session_state['matrix_lookup'] = df_new_matrix
            st.session_state['show_success'] = True
            st.session_state['success_time'] = time.time()
        else:
            st.error("❌ Matrix upload failed: Missing required columns.")

    # === Single-click download ===
    st.download_button(
        label="⬇️ Download Current Matrix CSV",
        data=st.session_state['matrix_lookup'].to_csv(index=False).encode('utf-8'),
        file_name="matrix_current.csv",
        mime="text/csv"
    )

# === SUCCESS BANNER DISPLAY (Auto-hide after 3 seconds) ===
if st.session_state['show_success']:
    st.success("✅ Matrix loaded successfully!")
    if time.time() - st.session_state['success_time'] > 3:
        st.session_state['show_success'] = False

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    st.success(f"✅ {uploaded_file.name} uploaded!")

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

    with st.expander("📏 Photometric Parameters + Metadata + Base Values", expanded=False):
        # === IES Metadata ===
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # === Photometric Parameters ===
        st.markdown("#### Photometric Parameters")
        photometric_data = [
            {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]} (Total number of lamps in test)"},
            {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]} lm (Luminous flux per lamp)"},
            {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]} (Scaling factor applied to candela values)"},
            {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]} (Number of vertical angles measured)"},
            {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]} (Number of horizontal angles measured)"},
            {"Parameter": "Photometric Type", "Details": f"{photometric_params[5]} (0=Type A, 1=Type B, 2=Type C)"},
            {"Parameter": "Units Type", "Details": f"{photometric_params[6]} (1=Feet, 2=Meters)"},
            {"Parameter": "Width", "Details": f"{photometric_params[7]} m (Width of luminaire for Type C files)"},
            {"Parameter": "Length", "Details": f"{photometric_params[8]} m (Length of luminaire for Type C files)"},
            {"Parameter": "Height", "Details": f"{photometric_params[9]} m (Height of luminaire for Type C files)"},
            {"Parameter": "Ballast Factor", "Details": f"{photometric_params[10]} (Factor applied to lumens for ballast losses)"},
            {"Parameter": "Future Use", "Details": f"{photometric_params[11]} (Reserved for future use)"},
            {"Parameter": "Input Watts", "Details": f"{photometric_params[12]} W (Input power measured during test)"}
        ]
        st.table(pd.DataFrame(photometric_data))

        # === Base Values ===
        st.markdown("#### Base Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Base LED Chip", "LED Base": "G1 (Gen1 Spec: per TM30 Report XXX)"},
            {"Description": "Base Design", "LED Base": "6S/4P/14.4W/280/400mA/G1/DR12w"}
        ]
        st.table(pd.DataFrame(base_values))

else:
    st.info("📄 Upload your IES file to proceed.")

# === FOOTER ===
st.caption("Version 4.3 - Unified Metadata + Base Values + Tooltips ✅")
