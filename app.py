import streamlit as st
import pandas as pd
import numpy as np

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
        matrix_file = st.file_uploader("Upload Matrix CSV", type=["csv"])
        if matrix_file:
            st.session_state['matrix_lookup'] = pd.read_csv(matrix_file)
            st.success(f"Matrix Uploaded: {matrix_file.name}")

        # ADVANCED LED PARAMETERS
        st.markdown("### Advanced LED Parameters")
        led_pitch_set = st.number_input("LED Pitch Set (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        leds_per_pitch_set = st.number_input("LEDs per Pitch Set", min_value=1, max_value=12, value=6)

        # COMPONENT LENGTHS
        st.markdown("### Component Lengths")
        end_plate_thickness = st.number_input("End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1)
        pir_length = st.number_input("PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        spitfire_length = st.number_input("Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)

        # Unlock Advanced Mode
        if st.button("Unlock Advanced Settings"):
            st.session_state['advanced_unlocked'] = True
            st.warning("Super Advanced Users Only: Changes require mandatory comments!")

        if st.session_state['advanced_unlocked']:
            comment = st.text_area("Mandatory Comment", placeholder="Explain why you are making changes")
            if not comment:
                st.error("Comment is mandatory to proceed with changes!")

# === MAIN PAGE ===
st.subheader("📄 IES Metadata")
uploaded_ies = st.file_uploader("Upload your IES file", type=["ies"])
if uploaded_ies:
    file_content = uploaded_ies.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_ies.name, 'content': file_content}]
    st.success(f"{uploaded_ies.name} uploaded!")

# === FUNCTIONS ===
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

def compute_lumen_data(photometric_params):
    if len(photometric_params) < 13:
        return None, None, None, None
    total_lumens = round(photometric_params[12], 1)
    input_watts = round(photometric_params[10], 1)
    efficacy_lm_per_w = round(total_lumens / input_watts, 1) if input_watts > 0 else 0
    lumens_per_m = round(total_lumens / photometric_params[8], 1) if photometric_params[8] > 0 else 0
    return total_lumens, input_watts, efficacy_lm_per_w, lumens_per_m

# === DISPLAY PHOTOMETRIC + COMPUTED BASELINE ===
if st.session_state['ies_files']:
    st.subheader("📏 Photometric Parameters")
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params = parse_ies_file(ies_file['content'])

    total_lumens, input_watts, efficacy_lm_per_w, lumens_per_m = compute_lumen_data(photometric_params)

    st.subheader("✨ Computed Baseline Data")
    baseline_data = [
        {"Description": "Total Lumens", "Value": total_lumens},
        {"Description": "Input Watts", "Value": input_watts},
        {"Description": "Efficacy (lm/W)", "Value": efficacy_lm_per_w},
        {"Description": "Lumens per Meter", "Value": lumens_per_m}
    ]
    baseline_df = pd.DataFrame(baseline_data)
    st.table(baseline_df.style.format({"Value": "{:.1f}"}))

# === FOOTER ===
st.caption("Version 2.1a - Sidebar Customisation, IES Metadata, Photometric & Baseline Display.")
