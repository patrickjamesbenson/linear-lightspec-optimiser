import streamlit as st
import pandas as pd
import numpy as np
import time
import io
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="IES Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_version' not in st.session_state:
    st.session_state['matrix_version'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False
if 'maintenance_access' not in st.session_state:
    st.session_state['maintenance_access'] = False

# === FUNCTIONS ===
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
    return round(total_flux * symmetry_factor, 1)

# === SIDEBAR ===
with st.sidebar:
    st.header("Customisation")
    st.subheader("Advanced LED Parameters")

    led_pitch_set = st.number_input(
        "LED Pitch Set (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1,
        help="Distance between LED pitch sets, defaults to 46mm for Zhaga compliance."
    )
    leds_per_pitch_set = st.number_input(
        "LEDs per Pitch Set", min_value=1, max_value=12, value=6,
        help="Number of LEDs in each pitch set."
    )
    series_number = st.number_input(
        "LED Series Number", min_value=1, max_value=12, value=3,
        help="Controls LED density. Higher series = higher density."
    )

    st.subheader("Component Lengths")
    end_plate_thickness = st.number_input(
        "End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1,
        help="Thickness of luminaire end plates. Affects total length."
    )
    pir_length = st.number_input(
        "PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1,
        help="Length allocated for PIR sensors."
    )
    spitfire_length = st.number_input(
        "Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1,
        help="Length allocated for Spitfire emergency lights."
    )

    if st.button("Unlock Advanced Settings"):
        st.session_state['advanced_unlocked'] = True
        st.warning("⚠️ Super Advanced Users Only! Comment mandatory to proceed.")

    if st.session_state['advanced_unlocked']:
        comment = st.text_area("Mandatory Comment", placeholder="Explain changes...")
        if not comment:
            st.error("You must enter a comment to proceed!")

# === MAIN PAGE ===

# === IES METADATA & COMPUTED BASELINE ===
with st.expander("IES Metadata & Computed Baseline", expanded=True):
    uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])
    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    if st.session_state['ies_files']:
        ies_file = st.session_state['ies_files'][0]
        header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])
        calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
        input_watts = photometric_params[12]
        length_m = photometric_params[8]
        calculated_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
        calculated_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

        baseline_data = [
            {"Description": "Total Lumens", "Value": calculated_lumens},
            {"Description": "Input Watts", "Value": input_watts},
            {"Description": "Efficacy (lm/W)", "Value": calculated_lm_per_watt},
            {"Description": "Lumens per Meter", "Value": calculated_lm_per_m}
        ]
        st.table(pd.DataFrame(baseline_data).style.format({"Value": "{:.1f}"}))

# === SCALING TOOL / LENGTH OPTIMISATION ===
with st.expander("Length Optimisation & Scaling Tool", expanded=False):
    st.info("Specify your desired luminaire length. We'll optimise for efficient board/component use.")
    target_length = st.number_input("Target Length (mm)", min_value=500, max_value=50000, step=1000, value=3000)
    st.caption("Results display optimal lengths (lower/higher) based on your component selection.")
    # Placeholder scaling logic
    optimal_lower = target_length - 50
    optimal_upper = target_length + 50
    st.write(f"Closest Lower Option: {optimal_lower} mm")
    st.write(f"Closest Higher Option: {optimal_upper} mm")

# === MATRIX UPLOAD/DOWNLOAD ===
with st.expander("Matrix Upload / Download", expanded=False):
    st.caption("✅ Download the current version before editing. Keep format consistent for re-upload.")
    if st.session_state['matrix_lookup'].empty:
        st.warning("⚠️ No matrix loaded yet.")

    uploaded_matrix = st.file_uploader("Upload Matrix CSV", type=["csv"])
    if uploaded_matrix:
        st.session_state['matrix_lookup'] = pd.read_csv(uploaded_matrix)
        version_timestamp = datetime.now().timestamp()
        st.session_state['matrix_version'].append(version_timestamp)
        st.success(f"Matrix uploaded. Version: {version_timestamp}")

    if not st.session_state['matrix_lookup'].empty:
        st.download_button(
            "Download Current Matrix Version",
            data=st.session_state['matrix_lookup'].to_csv(index=False).encode('utf-8'),
            file_name="current_matrix.csv"
        )
        st.write(f"Matrix Version Timestamp: {st.session_state['matrix_version'][-1] if st.session_state['matrix_version'] else 'None'}")

# === LOOKUP TABLE ===
with st.expander("Lookup Table (Mapped Items Only)", expanded=False):
    if not st.session_state['matrix_lookup'].empty:
        st.table(
            st.session_state['matrix_lookup'][['Diffuser / Louvre Description', 'Driver Description', 'CRI Description', 'CCT/Colour Description']].head(20)
        )
    else:
        st.warning("⚠️ Load a matrix to display lookup items.")

# === FOOTER ===
st.caption("Linear LightSpec Optimiser V2.1 © 2024")
