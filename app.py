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
    st.session_state['end_plate_thickness'] = 5.5  # mm
    st.session_state['led_pitch'] = 56.0  # mm
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lm_per_watt_increment'] = 115
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    # MOCK parsing the IES file (swap this out with actual parser later)
    file_name = uploaded_file.name
    base_luminaire_name = "BLine 8585D"
    optic = "Diffused Down"
    cri = "80CRI"
    cct = "3000K"
    base_lm_per_m = 400.0
    base_w_per_m = 11.6

    st.markdown("📂 **Base File Summary (IES Metadata + Photometric Parameters)**")
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        st.text("IES Version\nTest Info\nManufacturer\nLuminaire Catalog Number\nLuminaire Description\nIssued Date")
    with meta_col2:
        st.text("IESNA:LM-63-2002\n[TEST]\n[MANUFAC] Evolt Manufacturing\n[LUMCAT] B852-__A3___1488030ZZ\n"
                f"[LUMINAIRE] {base_luminaire_name} 11.6W - {cri} - {cct}\n[ISSUEDATE] 2024-07-07")

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | "
                    f"LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            col1, col2 = st.columns(2)
            st.session_state['end_plate_thickness'] = col1.number_input(
                "End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1
            )
            st.session_state['led_pitch'] = col2.number_input(
                "LED Series Module Pitch (mm)", min_value=10.0, value=st.session_state['led_pitch'], step=1.0
            )

    # === SELECT LENGTHS ===
    with st.expander("Select Lengths", expanded=True):
        desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")

        desired_length_mm = desired_length_m * 1000
        end_plate_thickness = st.session_state['end_plate_thickness']
        led_pitch = st.session_state['led_pitch']

        led_count = int((desired_length_mm - 2 * end_plate_thickness) // led_pitch)

        min_length_mm = led_count * led_pitch + 2 * end_plate_thickness
        max_length_mm = (led_count + 1) * led_pitch + 2 * end_plate_thickness

        shorter_length_m = round(min_length_mm / 1000, 3)
        longer_length_m = round(max_length_mm / 1000, 3)

        col1, col2 = st.columns(2)

        if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
            st.session_state['lengths_list'].append(shorter_length_m)
            st.session_state['locked'] = True
            st.rerun()

        if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
            st.session_state['lengths_list'].append(longer_length_m)
            st.session_state['locked'] = True
            st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        st.session_state['led_efficiency_gain_percent'] = st.number_input(
            "LED Chipset Adjustment (%)",
            min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0
        )
        st.session_state['efficiency_reason'] = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )

    # === SYSTEM LM/W INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']:.1f} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input(
                "Average lm/W Step Increment",
                min_value=10.0, max_value=500.0,
                value=st.session_state['lm_per_watt_increment'], step=1.0
            )

    # === SELECTED LENGTHS TABLE ===
    st.markdown("📏 **Selected Lengths for IES Generation**")
    if st.session_state['lengths_list']:
        table_rows = []
        efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts else 0.0

            luminaire_file_name = f"{base_luminaire_name} {optic}_{length:.3f}m_Professional"

            row = {
                "Delete": idx,
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri,
                "CCT": cct,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": st.session_state['efficiency_reason']
            }

            table_rows.append(row)

        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for idx, row in enumerate(table_rows):
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.rerun()

            row_data = [
                row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]
            ]

            for col, val in zip(cols[1:], row_data):
                col.write(val)

        # CSV EXPORT
        export_df = pd.DataFrame(table_rows).drop(columns=["Delete"])
        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'),
                           file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")

        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1) if target_lux else 0

        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int((required_change_lm_per_m / st.session_state['lm_per_watt_increment']) + 0.999) if required_change_lm_per_m >= st.session_state['lm_per_watt_increment'] else 0

        if difference_percent > 0:
            if increments_needed >= 1:
                st.warning(f"⚠️ Consider reducing by {increments_needed} increments.")
            else:
                st.warning(f"⚠️ Dimming recommended to match target lux.")
        elif difference_percent < 0:
            st.success(f"✅ Consider increasing by {increments_needed} increments or selecting a higher output IES file.")
        else:
            st.info("Target lux achieved precisely.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")
