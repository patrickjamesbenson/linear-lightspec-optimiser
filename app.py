import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="IES Metadata & Baseline Lumen Calculator", layout="wide")
st.title("IES Metadata & Computed Baseline Display")

# === SESSION STATE INITIALISATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
    st.session_state['selected_file_index'] = 0

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'].append({
        'name': uploaded_file.name,
        'content': file_content
    })

# === FUNCTION DEFINITIONS ===
def parse_ies_file(file_content):
    lines = file_content.splitlines()
    header_lines = []
    tilt_line = ''
    data_lines = []
    reading_data = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TILT"):
            tilt_line = stripped
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

    return round(total_flux * symmetry_factor, 2)

# === SELECT FILE TO DISPLAY ===
if st.session_state['ies_files']:
    file_names = [f["name"] for f in st.session_state['ies_files']]

    cols = st.columns([8, 2])
    selected = cols[0].radio("Select an IES file to view its baseline calculation:", range(len(file_names)),
                             format_func=lambda x: file_names[x],
                             index=st.session_state['selected_file_index'])

    # Delete button
    if cols[1].button("Delete Selected File"):
        del st.session_state['ies_files'][selected]
        if st.session_state['selected_file_index'] >= len(st.session_state['ies_files']):
            st.session_state['selected_file_index'] = max(0, len(st.session_state['ies_files']) - 1)
        st.experimental_rerun()

    # Update selection
    st.session_state['selected_file_index'] = selected

    # === PROCESS SELECTED FILE ===
    selected_file = st.session_state['ies_files'][selected]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(selected_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    calculated_lm_per_watt = round(calculated_lumens / input_watts, 2) if input_watts > 0 else 0

    # === DISPLAY COMPUTED BASELINE ===
    st.markdown("## ✨ Computed Baseline Data")
    st.metric(label="Calculated Total Lumens (lm)", value=f"{calculated_lumens}")
    st.metric(label="Calculated Lumens per Watt (lm/W)", value=f"{calculated_lm_per_watt}")
    st.info("All displayed computed values are generated dynamically based on the uploaded IES file and serve as a verification baseline.")

    # === DISPLAY IES METADATA ===
    st.markdown("## 📄 IES Metadata")
    meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

    st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    # === DISPLAY PHOTOMETRIC PARAMETERS ===
    st.markdown("## 📐 Photometric Parameters")

    photometric_data = [
        {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]} lamp(s) used"},
        {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]} lm (absolute photometry)" if photometric_params[1] < 0 else f"{photometric_params[1]} lm"},
        {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]:.1f} (multiplier applied to candela values)"},
        {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]} vertical angles measured"},
        {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]} horizontal planes"},
        {"Parameter": "Photometric Type", "Details": f"{photometric_params[5]} (Type C)" if photometric_params[5] == 1 else f"{photometric_params[5]} (Other)"},
        {"Parameter": "Units Type", "Details": f"{photometric_params[6]} (Meters)" if photometric_params[6] == 2 else f"{photometric_params[6]} (Feet)"},
        {"Parameter": "Width", "Details": f"{photometric_params[7]:.2f} m"},
        {"Parameter": "Length", "Details": f"{photometric_params[8]:.2f} m"},
        {"Parameter": "Height", "Details": f"{photometric_params[9]:.2f} m"},
        {"Parameter": "Ballast Factor", "Details": f"{photometric_params[10]:.1f}"},
        {"Parameter": "Future Use", "Details": f"{photometric_params[11]} (reserved)"},
        {"Parameter": "Input Watts", "Details": f"{photometric_params[12]:.1f} W"}
    ]

    photometric_df = pd.DataFrame(photometric_data)
    st.table(photometric_df)

else:
    st.warning("Please upload at least one IES file to proceed.")
