import streamlit as st
from utils import (
    parse_ies_file,
    validate_lengths,
    calculate_recommendations,
    generate_ies_files_zip
)

st.set_page_config(
    page_title="Linear LightSpec Optimiser - Powered by Evolt",
    page_icon="💡",
    layout="centered"
)

st.title("Linear LightSpec Optimiser")
st.caption("Fast, Accurate, Build-Ready Photometric Files - Powered by Evolt")

# Initialize session state for length selections
if "selected_lengths" not in st.session_state:
    st.session_state.selected_lengths = []

# File Upload Section
uploaded_file = st.file_uploader("Upload IES File", type=["ies"])

if uploaded_file:
    # Parse IES data (currently placeholder data from utils)
    ies_data = parse_ies_file(uploaded_file)

    st.subheader("Base IES Data")
    st.write(f"**Luminaire Name:** {ies_data['luminaire_name']}")
    st.write(f"**Base IES Length:** {ies_data['length_m']:.3f} m")
    st.write(f"**Lumens/metre:** {ies_data['lumens_per_m']:.1f} lm/m")
    st.write(f"**Watts/metre:** {ies_data['watts_per_m']:.2f} W/m")
    st.write(f"**Efficacy:** {ies_data['efficacy']:.2f} lm/W")

    # Length Validation Section
    st.subheader("Buildable Length Selection")
    desired_length_m = st.number_input("Enter Desired Length (m)", min_value=0.571, value=3.0, step=0.001)

    shorter_len, longer_len = validate_lengths(desired_length_m)

    st.markdown("### Select a Buildable Length")
    length_choice = st.radio("", [f"{shorter_len:.3f} m", f"{longer_len:.3f} m"])

    if st.button("Add Length to List"):
        # Convert string back to float, strip ' m'
        length_value = float(length_choice.replace(" m", ""))
        if length_value not in st.session_state.selected_lengths:
            st.session_state.selected_lengths.append(length_value)
            st.success(f"Added {length_value:.3f} m to lengths list.")

    if st.session_state.selected_lengths:
        st.markdown("### Selected Lengths:")
        for l in st.session_state.selected_lengths:
            st.write(f"- {l:.3f} m")

    # Lighting Design Efficiency Optimisation Expander
    with st.expander("Lighting Design Efficiency Optimisation"):
        achieved_lux = st.number_input("Achieved Lux in Design", min_value=1.0, value=365.0)
        target_lux = st.number_input("Target Lux in Design", min_value=1.0, value=240.0)

    # LED Efficiency Gain
    efficiency_gain = st.number_input("LED Efficiency Gain (%)", value=0.0)

    # Advanced Section
    with st.expander("Advanced (Use with Caution!)"):
        confirm = st.checkbox("I understand I am changing critical component sizes")
        if confirm:
            end_plate_mm = st.number_input("End Plate Expansion Gutter (mm)", value=5.5)
            led_pitch_mm = st.number_input('LED "Series Module" Pitch (mm)', value=56.0)
        else:
            end_plate_mm = 5.5
            led_pitch_mm = 56.0

    # Process Request
    if st.session_state.selected_lengths:
        if st.button("Process Request"):
            # Prepare and process data for each selected length
            results = []
            for length in st.session_state.selected_lengths:
                rec = calculate_recommendations(
                    ies_data,
                    achieved_lux,
                    target_lux,
                    efficiency_gain,
                    length
                )
                results.append(rec)

            zip_bytes = generate_ies_files_zip(results, end_plate_mm, led_pitch_mm)
            st.download_button(
                label="Download Optimised IES ZIP",
                data=zip_bytes,
                file_name="Optimised_IES_Files.zip",
                mime="application/zip"
            )
    else:
        st.warning("Please select at least one valid length before processing.")
