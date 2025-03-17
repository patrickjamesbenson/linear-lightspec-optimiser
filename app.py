import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()

# === DEFAULT MATRIX LOAD ===
default_matrix_path = "Matrix Headers.csv"
if os.path.exists(default_matrix_path):
    matrix_df = pd.read_csv(default_matrix_path)
    st.session_state['matrix_lookup'] = matrix_df
else:
    st.warning("⚠️ Matrix file not found. Upload manually below.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Matrix Upload / Download")

    matrix_file = st.file_uploader("Upload Matrix CSV (Optional)", type=["csv"])
    if matrix_file:
        df_new_matrix = pd.read_csv(matrix_file)
        required_columns = [
            'Option Code', 'Option Description',
            'Diffuser / Louvre Code', 'Diffuser / Louvre Description',
            'Driver Code', 'Driver Description',
            'Dimensions Code', 'Dimensions Description',
            'CRI Code', 'CRI Description',
            'CCT/Colour Code', 'CCT/Colour Description'
        ]
        if all(col in df_new_matrix.columns for col in required_columns):
            st.session_state['matrix_lookup'] = df_new_matrix
        else:
            st.error("❌ Matrix missing required columns.")

    st.download_button(
        label="⬇️ Download Current Matrix CSV",
        data=st.session_state['matrix_lookup'].to_csv(index=False).encode('utf-8'),
        file_name="matrix_current.csv",
        mime="text/csv"
    )

# === IES FILE UPLOAD ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === FUNCTION DEFINITIONS ===
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
        ies_file['content']
    )

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    # === DISPLAY PHOTOMETRIC PARAMETERS ===
    with st.expander("📏 Photometric Parameters + Metadata", expanded=True):
        st.markdown("#### IES Metadata")
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("#### Photometric Parameters")
        photometric_data = [
            {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]}"},
            {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]}"},
            {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]:.1f}"},
            {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]}"},
            {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]}"},
            {"Parameter": "Photometric Type", "Details": f"{photometric_params[5]}"},
            {"Parameter": "Units Type", "Details": f"{photometric_params[6]}"},
            {"Parameter": "Width (m)", "Details": f"{photometric_params[7]:.3f}"},
            {"Parameter": "Length (m)", "Details": f"{photometric_params[8]:.3f}"},
            {"Parameter": "Height (m)", "Details": f"{photometric_params[9]:.3f}"},
            {"Parameter": "Ballast Factor", "Details": f"{photometric_params[10]}"},
            {"Parameter": "Future Use", "Details": f"{photometric_params[11]}"},
            {"Parameter": "Input Watts", "Details": f"{photometric_params[12]:.1f}"}
        ]
        photometric_df = pd.DataFrame(photometric_data)
        st.table(photometric_df)

    # === BASE VALUES ===
    with st.expander("✨ Base Values", expanded=True):
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Base LED Chip", "LED Base": "G1"},
            {"Description": "Base Design", "LED Base": "6S/4P/14.4W/400mA/280mm/G1/DR12W"}
        ]
        base_df = pd.DataFrame(base_values)
        st.table(base_df)

    # === LUMCAT / MATRIX LOOKUP DATA ===
    with st.expander("🔎 LumCAT Reverse Lookup (from Matrix)", expanded=True):
        lumcat_data = {
            "Option Code": "BSA3AAA1",  # Example
            "Diffuser Code": "488",      # Example
            "Driver Code": "030",        # Example
            "CRI Code": "80",            # Example
            "CCT Code": "30",            # Example
            "Driver Type": "DR12W"       # Example
        }
        st.table(pd.DataFrame.from_dict(lumcat_data, orient='index', columns=['Value']))

else:
    st.info("📄 Upload your IES file to proceed.")

# === FOOTER ===
st.caption("Version 4.3 - Unified Base Info & Matrix ✅")
