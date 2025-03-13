import streamlit as st
import pandas as pd
import datetime
import io

# Initialize session state variables
if 'base_ies_data' not in st.session_state:
    st.session_state.base_ies_data = None
if 'selected_lengths' not in st.session_state:
    st.session_state.selected_lengths = []
if 'base_build_locked' not in st.session_state:
    st.session_state.base_build_locked = False
if 'led_adjustment' not in st.session_state:
    st.session_state.led_adjustment = 0
if 'led_adjustment_reason' not in st.session_state:
    st.session_state.led_adjustment_reason = ""
if 'lm_per_w_step' not in st.session_state:
    st.session_state.lm_per_w_step = 115
if 'uploaded_ies_files' not in st.session_state:
    st.session_state.uploaded_ies_files = []

# Function to parse IES file and extract metadata
def parse_ies_file(file):
    content = file.read().decode('utf-8')
    lines = content.splitlines()
    metadata = {}
    for line in lines:
        if line.startswith("["):
            key = line.split("]")[0] + "]"
            value = line[len(key):].strip()
            metadata[key] = value
    return metadata, content

# Function to calculate lumens per watt from IES data
def calculate_lm_per_watt(ies_data):
    # Placeholder for actual calculation logic
    return 115.0

# Function to add a length to the selected lengths table
def add_length(length, lm_per_watt):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    luminaire_name = f"Bline-Diffuser-{length}m-{timestamp}"
    st.session_state.selected_lengths.append({
        'length': length,
        'luminaire_name': luminaire_name,
        'lm_per_watt': lm_per_watt,
        'timestamp': timestamp
    })

# Function to delete a length from the selected lengths table
def delete_length(index):
    st.session_state.selected_lengths.pop(index)
    if len(st.session_state.selected_lengths) == 0:
        st.session_state.base_build_locked = False

# Function to lock the base build methodology
def lock_base_build():
    st.session_state.base_build_locked = True

# Function to unlock the base build methodology
def unlock_base_build():
    st.session_state.base_build_locked = False

# Function to handle LED adjustment changes
def handle_led_adjustment():
    if st.session_state.led_adjustment != 0 and not st.session_state.led_adjustment_reason:
        st.warning("Please provide a reason for the LED adjustment.")
    else:
        st.session_state.base_build_locked = True

# Function to handle lm/W step increment changes
def handle_lm_per_w_step():
    st.session_state.base_build_locked = True

# Function to generate IES files and CSV
def generate_files():
    if not st.session_state.selected_lengths:
        st.warning("Please add at least one length before generating files.")
        return

    # Generate IES files and CSV
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for length_info in st.session_state.selected_lengths:
            ies_filename = f"{length_info['luminaire_name']}.ies"
            ies_content = f"IES data for {length_info['luminaire_name']}"
            zf.writestr(ies_filename, ies_content)
        csv_filename = "luminaire_data.csv"
        csv_content = pd.DataFrame(st.session_state.selected_lengths).to_csv(index=False)
        zf.writestr(csv_filename, csv_content)

    st.download_button(
        label="Download IES and CSV files",
        data=zip_buffer.getvalue(),
        file_name="luminaire_files.zip",
        mime="application/zip"
    )

    # Clear session state
    st.session_state.selected_lengths = []
    st.session_state.uploaded_ies_files = []
    st.session_state.base_ies_data = None
    st.session_state.base_build_locked = False
    st.session_state.led_adjustment = 0
    st.session_state.led_adjustment_reason = ""
    st.session_state.lm_per_w_step = 115

# Main application
st.title("Linear LightSpec Optimiser")

# Section 1: Base IES File Upload
st.header("Upload your Base IES file")
base_ies_file = st.file_uploader("Choose an IES file", type=["ies"])
if base_ies_file:
    metadata, content = parse_ies_file(base_ies_file)
    st.session_state.base_ies_data = {'metadata': metadata, 'content': content}
    st.success("Base IES file uploaded successfully!")

# Display IES Metadata
if st.session_state.base_ies_data:
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=True):
        st.subheader("IES Metadata")
        metadata_df = pd.DataFrame(list(st.session_state.base_ies_data['metadata'].items()), columns=["Parameter", "Value"])
        st.table(metadata_df)

# Section 2: Base Build Methodology
with st.expander("📂 Base Build Methodology", expanded=False):
    if st.session_state.base_build_locked:
        st.info("Base Build Methodology is locked because lengths have been added.")
    else:
        end_plate_gutter = st.number_input("End Plate Expansion Gutter (mm)", value=5.5, step=0.1)
        led_pitch = st.number_input("LED Series Module Pitch (mm)", value=56.0, step=0.1)
        st.session_state.base_build_locked = True

# Section 3: Select Lengths
st.subheader("Select Lengths")
desired_length = st.number_input("Desired Length (m)", value=1.0, step=0.1, format="%.3f")
shorter_length = desired_length - (end_plate_gutter / 1000)
longer_length = desired_length + (end_plate_gutter / 1000)
lm_per_watt = calculate_lm_per_watt(st.session_state.base_ies_data['content']) if st.session_state.base_ies_data else 115.0

col1, col2 = st.columns(2)
with col1:
    if st.button(f"Add Shorter Length ({shorter_length:.3f} m)"):
        add_length(shorter_length, lm_per_watt)
        lock_base_build()
with col2:
    if st.button(f"Add Longer Length ({longer_length:.3f} m)"):
        add_length(longer_length, lm_per_watt)
        lock_base_build()

# Display Selected Lengths Table
if st.session_state.selected_lengths:
    st.subheader("📏 Selected Lengths for IES Generation")
    lengths_df = pd.DataFrame(st.session_state.selected_lengths)
    for i, row in lengths_df.iterrows():
        col1, col2, col3, col4 = st.columns([1
::contentReference[oaicite:2]{index=2}
 
