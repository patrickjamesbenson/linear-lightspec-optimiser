import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

# === Upload IES File ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === Base File Summary ===
    st.subheader("Base File Summary")
    st.text(f"Header Lines: {len(parsed['header'])}")
    st.text(f"Data Lines: {len(parsed['data'])}")

    # === End Plate & LED Pitch ===
    st.markdown("## End Plate & LED Pitch Configuration")
    end_plate_thickness = st.number_input(
        "End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1
    )
    led_pitch = st.number_input(
        "LED Series Module Pitch (mm)", min_value=40.0, value=56.0, step=0.1
    )

    # === Length Validation ===
    st.markdown("## Length Validation")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.1)
    desired_length_mm = desired_length_m * 1000

    # Shorter / Longer Buildable Lengths
    min_length_mm = (int((desired_length_mm - end_plate_thickness * 2) / led_pitch)) * led_pitch + end_plate_thickness * 2
    max_length_mm = min_length_mm + led_pitch

    st.success(f"Shorter Buildable Length: {min_length_mm / 1000:.3f}m")
    st.success(f"Longer Buildable Length: {max_length_mm / 1000:.3f}m")

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

    # === Comparison Table ===
    st.markdown("## Comparison Table: Base vs Optimised")
    base_lm_per_m = 400  # Placeholder
    base_w_per_m = 20    # Placeholder

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

    lengths_to_generate = st.multiselect(
        "Select Additional Lengths (m)", [1.0, 2.0, 4.5, 6.0]
    )
    all_lengths = [desired_length_m] + lengths_to_generate
    files_to_zip = {}

    for length in all_lengths:
        scaled_data = modify_candela_data(parsed['data'], efficiency_multiplier)
        new_file = create_ies_file(parsed['header'], scaled_data)
        filename = f"Optimised_{length:.2f}m.ies"
        files_to_zip[filename] = new_file

    zip_buffer = create_zip(files_to_zip)

    st.download_button(
        label="Download Optimised IES ZIP",
        data=zip_buffer,
        file_name="Optimised_IES_Files.zip",
        mime="application/zip"
    )

    # === CSV Summary ===
    st.markdown("## CSV Summary")

    csv_summary = pd.DataFrame({
        "Length (m)": all_lengths,
        "Lumens per Metre": [new_lm_per_m] * len(all_lengths),
        "Watts per Metre": [new_w_per_m] * len(all_lengths),
        "LED Pitch (mm)": [led_pitch] * len(all_lengths),
        "End Plate (mm)": [end_plate_thickness] * len(all_lengths),
        "Efficiency Reason": [efficiency_reason] * len(all_lengths)
    })

    st.dataframe(csv_summary)

    st.download_button(
        label="Download CSV Summary",
        data=csv_summary.to_csv(index=False).encode('utf-8'),
        file_name="Optimised_Summary.csv",
        mime="text/csv"
    )

else:
    st.info("Upload an IES file to begin optimisation.")
