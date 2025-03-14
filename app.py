import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

# === SIDEBAR ===
with st.sidebar:
    st.subheader("⚙️ Advanced Settings")

    with st.expander("Customisation", expanded=False):
        # MATRIX UPLOAD / DOWNLOAD
        st.markdown("### 📁 Matrix Upload / Download")
        st.caption("✅ Download current version first. Edit carefully. Keep column headers identical.")

        matrix_file = st.file_uploader("Upload Matrix CSV", type=["csv"], help="Upload your matrix CSV file using the exact column headers. This ensures the lookup works correctly.")
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
                version_time = int(time.time())
                st.success(f"Matrix updated successfully! Version: {version_time}")
            else:
                st.error("Matrix upload failed. Please ensure all required columns are present.")

        # ADVANCED LED PARAMETERS
        st.markdown("### 🛠️ Advanced LED Parameters")
        led_pitch_set = st.number_input("LED Pitch Set (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1, help="Pitch between LED chipsets in mm.")
        leds_per_pitch_set = st.number_input("LEDs per Pitch Set", min_value=1, max_value=12, value=6, help="Number of LEDs within each pitch set.")

        # COMPONENT LENGTHS
        st.markdown("### 📏 Component Lengths")
        end_plate_thickness = st.number_input("End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1, help="End plate thickness in mm.")
        pir_length = st.number_input("PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1, help="PIR sensor length in mm.")
        spitfire_length = st.number_input("Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1, help="Spitfire emergency module length in mm.")

        # Unlock Advanced Mode
        if st.button("Unlock Advanced Settings"):
            st.session_state['advanced_unlocked'] = True
            st.warning("Super Advanced Users Only: Changes require mandatory comments!")

        if st.session_state['advanced_unlocked']:
            comment = st.text_area("Mandatory Comment", placeholder="Explain why you are making changes", help="Document your reason for making advanced changes.")
            if not comment:
                st.error("Comment is mandatory to proceed with changes!")

# === MAIN PAGE ===

# === IES FILE UPLOAD ===
st.subheader("📄 IES Metadata")
uploaded_ies = st.file_uploader("Upload your IES file", type=["ies"], help="Upload an IES photometric file to extract luminaire data.")
if uploaded_ies:
    file_content = uploaded_ies.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_ies.name, 'content': file_content}]
    st.success(f"{uploaded_ies.name} uploaded!")

# === FUNCTION DEFINITIONS ===
def parse_ies_file(file_content):
    lines = file_content.splitlines()
    header_lines = []
    data_lines = []
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
    return header_lines, photometric_params

def compute_lumen_data(photometric_params, scaling_factor):
    if len(photometric_params) < 13:
        return None, None, None, None
    base_lumens = photometric_params[12]
    total_lumens = round(base_lumens * (1 + scaling_factor / 100), 1)
    input_watts = round(photometric_params[10], 1)
    efficacy_lm_per_w = round(total_lumens / input_watts, 1) if input_watts > 0 else 0
    lumens_per_m = round(total_lumens / photometric_params[8], 1) if photometric_params[8] > 0 else 0
    return total_lumens, input_watts, efficacy_lm_per_w, lumens_per_m

# === DISPLAY PHOTOMETRIC PARAMETERS AND COMPUTED BASELINE ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params = parse_ies_file(ies_file['content'])

    st.subheader("📐 Photometric Parameters")
    photometric_data = [
        {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]}"},
        {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]}"},
        {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]}"},
        {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]}"},
        {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]}"},
        {"Parameter": "Photometric Type", "Details": f"{photometric_params[5]}"},
        {"Parameter": "Units Type", "Details": f"{photometric_params[6]}"},
        {"Parameter": "Width", "Details": f"{photometric_params[7]}"},
        {"Parameter": "Length", "Details": f"{photometric_params[8]}"},
        {"Parameter": "Height", "Details": f"{photometric_params[9]}"},
        {"Parameter": "Ballast Factor", "Details": f"{photometric_params[10]}"},
        {"Parameter": "Future Use", "Details": f"{photometric_params[11]}"},
        {"Parameter": "Input Watts", "Details": f"{photometric_params[12]}"},
    ]
    st.table(pd.DataFrame(photometric_data))

    st.subheader("✨ Computed Baseline Data")

    scaling_factor = st.number_input("LED Chip Efficiency Change (%)", min_value=-100.0, max_value=500.0, value=0.0, step=0.1, help="Input percentage increase or decrease in LED chip efficiency. E.g., enter 10 for 10% more lumens.")

    total_lumens, input_watts, efficacy_lm_per_w, lumens_per_m = compute_lumen_data(photometric_params, scaling_factor)

    baseline_data = [
        {"Description": "Total Lumens", "Value": total_lumens},
        {"Description": "Input Watts", "Value": input_watts},
        {"Description": "Efficacy (lm/W)", "Value": efficacy_lm_per_w},
        {"Description": "Lumens per Meter", "Value": lumens_per_m}
    ]
    st.table(pd.DataFrame(baseline_data).style.format({"Value": "{:.1f}"}))

# === FOOTER ===
st.caption("Version 2.1b - Matrix, Advanced Settings, Computed Baseline, Photometric Params with Tooltips.")
