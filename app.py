import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === STREAMLIT PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

# === INITIALISE SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
if 'chipset_locked' not in st.session_state:
    st.session_state['chipset_locked'] = False
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'end_plate_thickness' not in st.session_state:
    st.session_state['end_plate_thickness'] = 5.5
if 'led_pitch' not in st.session_state:
    st.session_state['led_pitch'] = 56.0
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0
if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = "Current Generation"
if 'efficiency_multiplier' not in st.session_state:
    st.session_state['efficiency_multiplier'] = 1.0
if 'recommended_factor' not in st.session_state:
    st.session_state['recommended_factor'] = 1.0

# === UPLOAD IES FILE ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        ies_version = next((line for line in parsed['header'] if line.startswith("IESNA")), "Not Found")
        test_info = next((line for line in parsed['header'] if line.startswith("[TEST]")), "[TEST] Not Found")
        manufac_info = next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "[MANUFAC] Not Found")
        lumcat_info = next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "[LUMCAT] Not Found")
        luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
        issuedate_info = next((line for line in parsed['header'] if line.startswith("[ISSUEDATE]")), "[ISSUEDATE] Not Found")

        metadata_dict = {
            "IES Version": ies_version,
            "Test Info": test_info,
            "Manufacturer": manufac_info,
            "Luminaire Catalog Number": lumcat_info,
            "Luminaire Description": luminaire_info,
            "Issued Date": issuedate_info
        }

        st.markdown("### IES Metadata")
        st.table(pd.DataFrame.from_dict(metadata_dict, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):

        if st.session_state['locked']:
            if st.button("🔓 Unlock Base Build Methodology"):
                st.session_state['locked'] = False
        else:
            if st.button("🔒 Lock Base Build Methodology"):
                st.session_state['locked'] = True

        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")

            st.session_state['end_plate_thickness'] = st.number_input(
                "End Plate Expansion Gutter (mm)",
                min_value=0.0,
                value=st.session_state['end_plate_thickness'],
                step=0.1
            )

            st.session_state['led_pitch'] = st.number_input(
                "LED Series Module Pitch (mm)",
                min_value=14.0,
                value=st.session_state['led_pitch'],
                step=0.1
            )

    # === SELECT LENGTHS ===
    st.markdown("## Select Lengths")

    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.1)
    desired_length_mm = desired_length_m * 1000

    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    if st.button(f"Add Shorter Buildable Length: {shorter_length_m} m"):
        st.session_state['lengths_list'].append(shorter_length_m)

    if st.button(f"Add Longer Buildable Length: {longer_length_m} m"):
        st.session_state['lengths_list'].append(longer_length_m)

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("LED Chipset Adjustment", expanded=True) as chipset_expander:
        led_chipset_adjustment = st.number_input(
            "LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
            value=st.session_state['led_efficiency_gain_percent'], step=1.0
        )

        reason = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )

        # Require reason if adjustment is non-zero
        if led_chipset_adjustment != 0 and reason.strip() == "":
            st.warning("Please enter a reason for the LED Chipset Adjustment before proceeding.")
            st.session_state['chipset_locked'] = False
        else:
            st.session_state['led_efficiency_gain_percent'] = led_chipset_adjustment
            st.session_state['efficiency_reason'] = reason
            st.session_state['efficiency_multiplier'] = 1 + (led_chipset_adjustment / 100)
            st.session_state['chipset_locked'] = True

    if not chipset_expander:
        st.session_state['chipset_locked'] = True

    # === LIGHTING DESIGN EFFICIENCY OPTIMISATION ===
    st.markdown("## Lighting Design Efficiency Optimisation")

    achieved_lux = st.number_input("Achieved Lux in Design", min_value=0.0, value=300.0, step=10.0)
    target_lux = st.number_input("Target Lux in Design", min_value=0.0, value=250.0, step=10.0)

    recommended_factor = (target_lux / achieved_lux) if achieved_lux else 1
    st.session_state['recommended_factor'] = recommended_factor

    st.metric("Recommended Lumens per Metre (factor)", f"{recommended_factor:.2f}x")

    # === LENGTH TABLE - ONLY IF CHIPSET LOCKED ===
    if st.session_state['chipset_locked'] and st.session_state['lengths_list']:
        st.markdown("### Selected Lengths for IES Generation")

        base_lm_per_m = 400
        base_w_per_m = 20

        length_table_data = []

        for length in st.session_state['lengths_list']:
            lm_per_m = base_lm_per_m * recommended_factor * st.session_state['efficiency_multiplier']
            w_per_m = base_w_per_m * recommended_factor
            total_lumens = lm_per_m * length
            total_watts = w_per_m * length

            length_table_data.append({
                "Length (m)": length,
                "Lumens per Metre": f"{lm_per_m:.2f}",
                "Watts per Metre": f"{w_per_m:.2f}",
                "Total Lumens (lm)": f"{total_lumens:.2f}",
                "Total Watts (W)": f"{total_watts:.2f}",
                "End Plate (mm)": st.session_state['end_plate_thickness'],
                "LED Series Pitch (mm)": st.session_state['led_pitch'],
                "LED Chipset Adjustment": f"{st.session_state['efficiency_multiplier']:.2f}",
                "LED Multiplier Reason": st.session_state['efficiency_reason'],
                "Product Tier": "Professional"
            })

        lengths_df = pd.DataFrame(length_table_data)

        st.table(lengths_df)

        st.download_button(
            "Download CSV Summary",
            data=lengths_df.to_csv(index=False).encode('utf-8'),
            file_name="Selected_Lengths_Summary.csv",
            mime="text/csv"
        )
    elif not st.session_state['chipset_locked']:
        st.info("Complete the LED Chipset Adjustment section to proceed.")

    # === PRODUCT TIER FEEDBACK ===
    st.markdown("## Product Tier Feedback (Draft Mode)")
    st.info("🛠️ Draft: Based on your inputs, this system suggests 'Professional' tier.")

    # === COMPARISON TABLE ===
    st.markdown("## Comparison Table: Base vs Optimised")

    base_lm_per_m = 400
    base_w_per_m = 20

    new_lm_per_m = base_lm_per_m * st.session_state['recommended_factor'] * st.session_state['efficiency_multiplier']
    new_w_per_m = base_w_per_m * st.session_state['recommended_factor']

    comparison_df = pd.DataFrame({
        "Metric": ["Lumens per Metre", "Watts per Metre"],
        "Base": [f"{base_lm_per_m:.2f}", f"{base_w_per_m:.2f}"],
        "Optimised": [f"{new_lm_per_m:.2f}", f"{new_w_per_m:.2f}"]
    })

    st.table(comparison_df)

    # === GENERATE OPTIMISED IES FILES ===
    st.markdown("## Generate Optimised IES Files")

    if st.session_state['chipset_locked'] and st.session_state['lengths_list']:
        if st.button("Generate IES Files & Download ZIP"):
            files_to_zip = {}

            for length in st.session_state['lengths_list']:
                scaled_data = modify_candela_data(parsed['data'], st.session_state['efficiency_multiplier'])
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

else:
    st.info("Upload an IES file to begin optimisation.")
