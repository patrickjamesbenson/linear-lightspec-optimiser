import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser v4.8-dev", layout="wide")
st.title("Linear Lightspec Optimiser v4.8-dev")

# === SESSION STATE INITIALIZATION ===
if 'dataset_loaded' not in st.session_state:
    st.session_state['dataset_loaded'] = False
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'selected_led_chip' not in st.session_state:
    st.session_state['selected_led_chip'] = None
if 'selected_ecg' not in st.session_state:
    st.session_state['selected_ecg'] = None

# === LOAD DATASET ===
dataset_file = st.sidebar.file_uploader("📁 Upload Dataset Excel", type=["xlsx"])
if dataset_file:
    try:
        dataset = pd.read_excel(dataset_file, sheet_name=None)
        st.session_state['dataset_loaded'] = True
        st.success("✅ Dataset loaded successfully!")

        # Pulling sheets
        matrix_lookup = dataset.get("Matrix Lookup", pd.DataFrame())
        led_chips = dataset.get("LED Chips", pd.DataFrame())
        ecg_drivers = dataset.get("ECG Drivers", pd.DataFrame())

    except Exception as e:
        st.error(f"❌ Error loading Excel: {e}")
        st.session_state['dataset_loaded'] = False

# === IES FILE UPLOAD ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    st.success(f"✅ {uploaded_file.name} uploaded!")

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

    return header_lines, photometric_params

# === DISPLAY PHOTOMETRIC PARAMETERS ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params = parse_ies_file(ies_file['content'])

    with st.expander("📏 Photometric Parameters + Base Values", expanded=True):
        st.markdown("### IES Metadata")
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("### Photometric Parameters (A-M)")
        param_labels = [
            ("A", "Lamps", photometric_params[0]),
            ("B", "Lumens/Lamp", photometric_params[1]),
            ("C", "Candela Mult.", photometric_params[2]),
            ("D", "Vert Angles", photometric_params[3]),
            ("E", "Horiz Angles", photometric_params[4]),
            ("F", "Photometric Type", photometric_params[5]),
            ("G", "Units Type", photometric_params[6]),
            ("H", "Width (m)", photometric_params[7]),
            ("I", "Length (m)", photometric_params[8]),
            ("J", "Height (m)", photometric_params[9]),
            ("K", "Ballast Factor", photometric_params[10]),
            ("L", "Future Use", photometric_params[11]),
            ("M", "Input Watts [F]", photometric_params[12])
        ]
        param_df = pd.DataFrame(param_labels, columns=["Param", "Description", "Value"])
        st.table(param_df)

# === LED CHIP SELECTION ===
if st.session_state.get('dataset_loaded'):
    st.subheader("🔧 LED Chip Selection")

    chip_names = led_chips['Chip'].tolist()
    selected_chip = st.selectbox("Select LED Chip", chip_names)

    chip_data = led_chips[led_chips['Chip'] == selected_chip].iloc[0]

    st.markdown(f"- **Chip Name:** {chip_data['Chip']}")
    st.markdown(f"- **lm@350mA:** {chip_data['LED lm @350mA']}")
    st.markdown(f"- **Engineering Safety Factor:** {chip_data['Engineering Safety Factor %']}%")

# === ECG SELECTION ===
if st.session_state.get('dataset_loaded'):
    st.subheader("⚡ ECG Driver Selection")

    ecg_names = ecg_drivers['ECG'].tolist()
    selected_ecg = st.selectbox("Select ECG Driver", ecg_names)

    ecg_data = ecg_drivers[ecg_drivers['ECG'] == selected_ecg].iloc[0]

    st.markdown(f"- **ECG Name:** {ecg_data['ECG']}")
    st.markdown(f"- **Max Output W:** {ecg_data['Max Output W']}")
    st.markdown(f"- **Engineering Safety Factor:** {ecg_data['Engineering Safety Factor %']}%")

# === FOOTER ===
st.caption("Version 4.8-dev - UI Integration Phase ✅")
