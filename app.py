import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    st.subheader("Base File Summary")
    st.text(f"Header Lines: {len(parsed['header'])}")
    st.text(f"Data Lines: {len(parsed['data'])}")

    # === End Plate & LED Pitch with Lock ===
    st.markdown("## End Plate & LED Pitch Configuration")

    if 'locked' not in st.session_state:
        st.session_state['locked'] = False
        st.session_state['lengths_list'] = []

    if not st.session_state['locked']:
        end_plate_thickness = st.number_input(
            "End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1
        )
        led_pitch = st.number_input(
            "LED Series Module Pitch (mm)", min_value=40.0, value=56.0, step=0.1
        )
        confirm_lock = st.checkbox("Confirm End Plate & LED Pitch (Do not edit unless you know what you're doing)")
        if confirm_lock:
            st.session_state['locked'] = True
            st.session_state['end_plate_thickness'] = end_plate_thickness
            st.session_state['led_pitch'] = led_pitch
    else:
        end_plate_thickness = st.session_state['end_plate_thickness']
        led_pitch = st.session_state['led_pitch']
        st.info(f"Locked: End Plate = {end_plate_thickness}mm | LED Pitch = {led_pitch}mm")
        if st.button("Unlock Settings"):
            st.session_state['locked'] = False

    # === Length Validation ===
    st.markdown("## Length Validation")

    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.1)
    desired_length_mm = desired_length_m * 1000

    min_length_mm = (int((desired_length_mm - end_plate_thickness * 2) / led_pitch)) * led_pitch + end_plate_thickness * 2
    max_length_mm = min_length_mm + led_pitch

    st.success(f"Shorter Buildable Length: {min_length_mm / 1000:.3f}m")
    st.success(f"Longer Buildable Length: {max_length_mm / 1000:.3f}m")

    # === Add Length Buttons ===
    if st.button("Add Shorter Length"):
        st.session_state['lengths_list'].append(round(min_length_mm / 1000, 3))

    if st.button("Add Longer Length"):
        st.session_state['lengths_list'].append(round(max_length_mm / 1000, 3))

    # === Show Selected Lengths ===
    if st.session_state['lengths_list']:
        st.markdown("### Selected Lengths for IES Generation")
        lengths_df = pd.DataFrame({
            "Selected Lengths (m)": st.session_state['lengths_list']
        })
        st.table(lengths_df)
    else:
        st.info("No lengths selected yet.")

    # === Lighting Design Efficiency Optimisation ===
    st.markdown("## Lighting Design Efficiency Optimisation")

    achieved_lux = st.number_input("Achieved Lux in Design", min_value=0.0, value=300.0, step=10.0)
    target_lux = st.number_input("Target Lux in Design", min_value=0.0, value=250.0, step=10.0)

    recommended_factor = (target_lux / achieved_lux) if achieved_lux else 1
    st.metric("Recommended Lumens per Metre (factor)", f"{recommended_factor:.2f}x")

    # === LED Efficiency Gain ===
    st.markdown("## LED Efficiency Gain")

    led_efficiency_gain_percent = st.number_input(
        "LED Efficiency Gain (%)", min_value=-50.0, max_value=100.0, value=0.0, step=1.0
    )
    efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value="")

    efficiency_multiplier = 1 + (led_efficiency_gain_percent / 100)

    # === Product Tier Feedback (Draft Mode) ===
    st.markdown("## Product Tier Feedback (Draft Mode)")
    st.info("🛠️ Draft: Based on your inputs, this system suggests 'Professional' tier.")

    # === Comparison Table ===
    st.markdown("## Comparison Table: Base vs Optimised")

    base_lm_per_m = 400  # Placeholder, parse later
    base_w_per_m = 20    # Placeholder, parse later

    new_lm_per_m = base_lm_per_m * recommended_factor * efficiency_multiplier
    new_w_per_m = base_w_per_m * recommended_factor

    comparison_df = pd.DataFrame({
        "Metric": ["Lumens per Metre", "Watts per Metre"],
        "Base": [f"{base_lm_per_m:.2f}", f"{base_w_per_m:.2f}"],
        "Optimised": [f"{new_lm_per_m:.2f}", f"{new_w_per_m:.2f}"]
    })

    st.table(comparison_df)

    # === Generate Optimised IES Files ===
    st.markdown("## Generate Optimised IES Files")

    if st.session_state['lengths_list']:
        if st.button("Generate IES Files & Download ZIP"):
            files_to_zip = {}

            for length in st.session_state['lengths_list']:
                scaled_data = modify_candela_data(parsed['data'], efficiency_multiplier)
                new_file = create_ies_file(parsed['header'], scaled_data)
                filename = f"Optimised_{length:.2f}m.ies"
                files_to_zip[filename] = new_file

            zip_buffer = create_zip(files_to_zip)

            st.download_button(
                "Download ZIP of IES Files",
                zip_buffer,
                file_name="Optimised_IES_Files.zip",
                mime="application/zip"
            )

    # === CSV Summary ===
    st.markdown("## CSV Summary")

    if st.session_state['lengths_list']:
        csv_summary = pd.DataFrame({
            "Length (m)": st.session_state['lengths_list'],
            "Lumens per Metre": [new_lm_per_m] * len(st.session_state['lengths_list']),
            "Watts per Metre": [new_w_per_m] * len(st.session_state['lengths_list']),
            "LED Pitch (mm)": [led_pitch] * len(st.session_state['lengths_list']),
            "End Plate (mm)": [end_plate_thickness] * len(st.session_state['lengths_list']),
            "Efficiency Reason": [efficiency_reason] * len(st.session_state['lengths_list'])
        })

        st.dataframe(csv_summary)

        st.download_button(
            "Download CSV Summary",
            data=csv_summary.to_csv(index=False).encode('utf-8'),
            file_name="Optimised_Summary.csv",
            mime="text/csv"
        )

else:
    st.info("Upload an IES file to begin optimisation.")
