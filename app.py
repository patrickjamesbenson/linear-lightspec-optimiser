import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

# Remove splash screen for stability testing
# def splash_screen():
#     st.image("assets/splash_screen.png", use_container_width=True)

# if "splash" not in st.session_state:
#     splash_screen()
#     st.session_state["splash"] = True

# Title
st.title("Linear LightSpec Optimiser")

# File upload
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    st.subheader("Base File Summary")
    st.text(f"Header Lines: {len(parsed['header'])}")
    st.text(f"Data Lines: {len(parsed['data'])}")

    # LED Efficiency Gain Input
    efficiency_gain_percent = st.number_input(
        "LED Efficiency Gain (%)", min_value=-50.0, max_value=100.0, value=0.0, step=1.0
    )
    
    reason = st.text_input(
        "Reason for Efficiency Gain (e.g., Gen 2 LED +15% increase lumen output)"
    )

    # Length Selection
    target_length_m = st.number_input(
        "Select Target Length (m)", min_value=0.5, max_value=10.0, value=1.0, step=0.1
    )

    # Modify Candela Data
    efficiency_multiplier = 1 + (efficiency_gain_percent / 100)
    modified_data = modify_candela_data(parsed['data'], efficiency_multiplier)

    # Create New IES Content
    new_ies_content = create_ies_file(parsed['header'], modified_data)

    # Download Section
    st.subheader("Download Your Files")

    files_to_download = {
        f"Optimised_{target_length_m}m.ies": new_ies_content
    }

    zip_buffer = create_zip(files_to_download)

    st.download_button(
        label="Download Optimised IES ZIP",
        data=zip_buffer,
        file_name="Optimised_IES_Files.zip",
        mime="application/zip"
    )

    st.success("Optimisation complete! Download your IES files.")

else:
    st.info("Please upload an IES file to begin.")
