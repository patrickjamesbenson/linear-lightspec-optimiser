import streamlit as st
import pandas as pd
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INIT ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = "Current Generation"
    st.session_state['lmw_increment'] = 115.0

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    base_filename = uploaded_file.name
    st.write(f"**{base_filename}**")
    
    # Dummy Metadata
    ies_metadata = {
        "IES Version": "IESNA:LM-63-2002",
        "Test Info": "[TEST]",
        "Manufacturer": "[MANUFAC] Evolt Manufacturing",
        "Luminaire Catalog Number": "[LUMCAT] B852-__A3___1488030ZZ",
        "Luminaire Description": "[LUMINAIRE] BLine 8585D 11.6W - 80CRI - 3000K",
        "Issued Date": "[ISSUEDATE] 2024-07-07"
    }
    
    photometric_params = {
        "Number of Lamps": 1,
        "Lumens per Lamp": -1,
        "Candela Multiplier": 1,
        "Vertical Angles": 91,
        "Horizontal Angles": 4,
        "Photometric Type": 1,
        "Units Type": 2,
        "Width (m)": 0.08,
        "Length (m)": 1,
        "Height (m)": 0.09,
        "Ballast Factor": 1,
        "Future Use": 1,
        "Input Watts": 11.6
    }

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        st.subheader("IES Metadata")
        st.table(pd.DataFrame(ies_metadata.items(), columns=["", "Value"]))
        st.subheader("Photometric Parameters")
        st.table(pd.DataFrame(photometric_params.items(), columns=["", "Value"]))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

    # === LENGTH SELECTION ===
    st.markdown("### Select Lengths")

    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000

    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    col1, col2 = st.columns(2)
    if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.session_state['locked'] = True
        st.experimental_rerun()

    if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True
        st.experimental_rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        st.session_state['led_efficiency_gain_percent'] = st.number_input(
            "LED Chipset Adjustment (%)",
            min_value=-50.0,
            max_value=100.0,
            value=st.session_state['led_efficiency_gain_percent'],
            step=1.0
        )

        st.session_state['efficiency_reason'] = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )

        if st.session_state['led_efficiency_gain_percent'] != 0 and st.session_state['efficiency_reason'].strip() == "":
            st.warning("⚠️ Reason is required for any non-zero adjustment.")

    # === SYSTEM LM/W EFFICIENCY INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.
        For advanced users only.
        """)

        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_increment']:.1f} lm/W")
        else:
            st.session_state['lmw_increment'] = st.number_input(
                "Average lm/W Step Increment",
                min_value=50.0,
                max_value=300.0,
                value=st.session_state['lmw_increment'],
                step=1.0
            )

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)

        table_rows = []
        for length in st.session_state['lengths_list']:
            total_lumens = round(base_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts else 0

            tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
            luminaire_file_name = f"BLine 8585D Diffused Down_{length:.3f}m_{tier}"

            table_rows.append({
                "Length (m)": length,
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": "80CRI",
                "CCT": "3000K",
                "Total Lumens": total_lumens,
                "Total Watts": total_watts,
                "Settings lm/W": lm_per_w,
                "Comments": st.session_state['efficiency_reason']
            })

        df = pd.DataFrame(table_rows)

        st.table(df)

        # === DELETE BUTTONS ===
        for idx, length in enumerate(st.session_state['lengths_list']):
            if st.button(f"Delete {length:.3f} m", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.experimental_rerun()

        # === CSV EXPORT ===
        csv_export = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV Summary", csv_export, "Selected_Lengths_Summary.csv", "text/csv")

    else:
        st.info("No lengths selected. Add lengths above.")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=True):
        st.subheader("Target vs Achieved Lux Levels")

        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        # Recommend increments
        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int(required_change_lm_per_m // st.session_state['lmw_increment'])

        if increments_needed < 1:
            st.warning(f"⚠️ Dimming recommended to match target lux.")
        else:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE IES FILES (PLACEHOLDER) ===
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")

else:
    st.info("Upload an IES file to begin optimisation.")
