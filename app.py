# Linear LightSpec Optimiser v4.8 - Full Streamlit App with IES File Parsing and Customer Builder
# No smoke. No mirrors. Just truth.

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# === CONFIG ===
ADMIN_PASSWORD = "your_secure_password"  # Replace with your secure password

# === SESSION STATE ===
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if 'dataset' not in st.session_state:
    st.session_state['dataset'] = None

if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []

# === ADMIN LOGIN PANEL ===
with st.sidebar:
    st.subheader("Admin Access")
    if not st.session_state['authenticated']:
        password_input = st.text_input("Enter Admin Password", type="password")
        if password_input == ADMIN_PASSWORD:
            st.session_state['authenticated'] = True
            st.success("Access granted")
        elif password_input:
            st.error("Incorrect password")

# === LOAD DATA FUNCTION ===
def load_local_excel(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        dataset = {
            'LumCAT_Config': pd.read_excel(xls, 'LumCAT_Config'),
            'ECG_Config': pd.read_excel(xls, 'ECG_Config'),
            'Tier_Rules_Config': pd.read_excel(xls, 'Tier_Rules_Config'),
            'LED_Chip_Config': pd.read_excel(xls, 'LED_Chip_Config'),
            'IES_Normalisation_Map': pd.read_excel(xls, 'IES_Normalisation_Map'),
            'Customer_View_Config': pd.read_excel(xls, 'Customer_View_Config')
        }
        return dataset
    except Exception as e:
        st.error(f"Error loading local Excel file: {e}")
        return {}

@st.cache_data(show_spinner=True)
def load_all_data():
    file_path = "Linear_Data.xlsx"  # Path to your local file (adjust as needed)
    return load_local_excel(file_path)

if st.session_state['dataset'] is None:
    with st.spinner("Loading data from local file..."):
        st.session_state['dataset'] = load_all_data()

# === IES FILE UPLOAD ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === IES PARSE FUNCTION ===
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

# === SIMPLE LUMEN CALCULATION ===
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

# === MAIN APP ===
st.title("Linear LightSpec Optimiser v4.8")
st.caption("No smoke. No mirrors. Just truth.")

if st.session_state['authenticated']:
    st.subheader("📊 Core Dataset Preview (Admin Only)")
    for name, df in st.session_state['dataset'].items():
        st.markdown(f"### {name}")
        st.dataframe(df.head(10))

# === IES FILE DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    with st.expander("📏 IES Parameters + Metadata + Derived Values", expanded=True):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("#### IES Parameters")
        photometric_table = [
            {"Description": "Lamps", "Value": f"{photometric_params[0]}"},
            {"Description": "Lumens/Lamp", "Value": f"{photometric_params[1]}"},
            {"Description": "Input Watts", "Value": f"{input_watts}"},
            {"Description": "Length (m)", "Value": f"{length_m}"},
        ]
        st.table(pd.DataFrame(photometric_table))

        st.markdown("#### Derived Values")
        base_values = [
            {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "Value": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "Value": f"{base_lm_per_m:.1f}"},
        ]
        st.table(pd.DataFrame(base_values))

# === CUSTOMER LUMINAIRE BUILDER ===
st.subheader("🔨 Customer Luminaire Builder")

if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

with st.form("luminaire_entry_form"):
    luminaire_name = st.text_input("Luminaire Name")
    tier_selection = st.selectbox("Select Tier", ["Core", "Professional", "Advanced"])
    length_input = st.number_input("Enter Required Length (mm)", min_value=280, step=10)
    notes_input = st.text_input("Notes (e.g., Room Name, Mounting Type)")
    submitted = st.form_submit_button("Add to Table")

    if submitted:
        new_entry = {
            'Luminaire Name': luminaire_name,
            'Tier': tier_selection,
            'Selected Length (mm)': length_input,
            'Notes': notes_input,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state['customer_entries'].append(new_entry)
        st.success("Luminaire added to table.")

st.markdown("### Current Luminaire Selections")
if st.session_state['customer_entries']:
    customer_df = pd.DataFrame(st.session_state['customer_entries'])
    st.dataframe(customer_df)

    csv = customer_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"luminaire_selections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.info("No luminaires added yet.")

# === FOOTER ===
st.caption(f"Version 4.8 - Powered by Local Dataset - {datetime.now().strftime('%Y-%m-%d')}")
