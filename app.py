import streamlit as st
from utils import (
    parse_ies_file,
    validate_lengths,
    calculate_recommendations,
    generate_ies_files_zip
)

st.set_page_config(page_title="Linear LightSpec Optimiser - Powered by Evolt")

st.title("Linear LightSpec Optimiser")
st.caption("Fast, Accurate, Build-Ready Photometric Files - Powered by Evolt")

# File Upload
uploaded_file = st.file_uploader("Upload IES File", type=["ies"])

if uploaded_file:
    # Parse IES data
    ies_data = parse_ies_file(uploaded_file)

    st.subheader("Base IES Data")
    st.write(f"Luminaire Name: {ies_data['luminaire_name']}")
    st.write(f"Original Length (m): {ies_data['length_m']:.3f}")
    st.write(f"Lumens/metre: {ies_data['lumens_per_m']:.1f}")
    st.write(f"Watts/metre: {ies_data['watts_per_m']:.2f}")
    st.write(f"Efficacy: {ies_data['efficacy']:.2f} lm/W")

    # User Inputs
    st.subheader("Optimisation Inputs")
    achieved_lux = st.number_input("Achieved Lux in Design", min_value=1.0, value=365.0)
    target_lux = st.number_input("Target Lux", min_value=1.0, value=240.0)
    efficiency_gain = st.number_input("LED Efficiency Gain (%)", value=0.0)

    # Custom Component Sizes
    with st.expander("Advanced (Use with Caution!)"):
        confirm = st.checkbox("I understand I am changing critical component sizes")
        if confirm:
            end_plate_mm = st.number_input("End Plate Thickness (mm)", value=5.5)
            led_pitch_mm = st.number_input("LED Board Pitch (mm)", value=56.0)
        else:
            end_plate_mm = 5.5
            led_pitch_mm = 56.0

    # Length Validation
    st.subheader("Length Validation")
    desired_length_m = st.number_input("Enter Desired Length (m)", min_value=0.571, value=3.0)
    shorter_len, longer_len = validate_lengths(desired_length_m, end_plate_mm, led_pitch_mm)

    st.write(f"Shorter Buildable Length: {shorter_len:.3f} m")
    st.write(f"Longer Buildable Length: {longer_len:.3f} m")

    length_choice = st.radio("Select a Buildable Length", [shorter_len, longer_len])

    if length_choice:
        st.success(f"Valid Length Selected: {length_choice:.3f} m")
        rec = calculate_recommendations(
            ies_data,
            achieved_lux,
            target_lux,
            efficiency_gain,
            length_choice
        )

        st.subheader("Optimised Output")
        st.write(f"Recommended Lumens/m: {rec['lumens_per_m']:.1f}")
        st.write(f"Recommended Watts/m: {rec['watts_per_m']:.2f}")
        st.write(f"Efficacy: {rec['efficacy']:.2f} lm/W")

        # Generate Files
        if st.button("Generate IES Files and ZIP"):
            zip_bytes = generate_ies_files_zip(rec, end_plate_mm, led_pitch_mm)
            st.download_button(
                label="Download IES ZIP",
                data=zip_bytes,
                file_name="Optimised_IES_Files.zip",
                mime="application/zip"
            )
