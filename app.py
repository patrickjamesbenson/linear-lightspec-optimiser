import streamlit as st
import pandas as pd
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INITIALISATION ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lmw_step_increment'] = 115.0
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    # Simulate reading file content
    base_filename = uploaded_file.name
    luminaire_name = "BLine 8585D"
    optic_name = "Diffused Down"
    cri = "80CRI"
    cct = "3000K"
    base_lm_per_m = 400.0
    base_w_per_m = 11.6

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        st.table(pd.DataFrame({
            "IES Version": ["IESNA:LM-63-2002"],
            "Test Info": ["[TEST]"],
            "Manufacturer": ["[MANUFAC] Evolt Manufacturing"],
            "Luminaire Catalog Number": ["[LUMCAT] B852-__A3___1488030ZZ"],
            "Luminaire Description": [f"[LUMINAIRE] {luminaire_name} 11.6W - {cri} - {cct}"],
            "Issued Date": ["[ISSUEDATE] 2024-07-07"]
        }).T.rename(columns={0: "Value"}))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

        # === LENGTH INPUT ===
        desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
        col1, col2 = st.columns(2)

        shorter_length = round(desired_length_m, 3)
        longer_length = round(desired_length_m + 0.05, 3)

        if col1.button(f"Add Shorter Buildable Length: {shorter_length:.3f} m"):
            st.session_state['lengths_list'].append(shorter_length)
            st.session_state['locked'] = True
            st.rerun()

        if col2.button(f"Add Longer Buildable Length: {longer_length:.3f} m"):
            st.session_state['lengths_list'].append(longer_length)
            st.session_state['locked'] = True
            st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_eff = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
        reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

        if led_eff != 0 and reason.strip() == "":
            st.error("⚠️ Please provide a reason for adjustment")
        else:
            st.session_state['led_efficiency_gain_percent'] = led_eff
            st.session_state['efficiency_reason'] = reason

    # === AVERAGE LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_step_increment']} lm/W")
        else:
            st.session_state['lmw_step_increment'] = st.number_input("Average lm/W Step Increment", min_value=50.0, max_value=200.0, value=st.session_state['lmw_step_increment'], step=1.0)

    # === SELECTED LENGTHS TABLE ===
    with st.expander("📏 Selected Lengths for IES Generation", expanded=False):
        if st.session_state['lengths_list']:
            table_rows = []
            eff_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
            new_w_per_m = round(base_w_per_m * eff_multiplier, 1)
            new_lm_per_m = round(base_lm_per_m, 1)

            for idx, length in enumerate(st.session_state['lengths_list']):
                total_lumens = round(new_lm_per_m * length, 1)
                total_watts = round(new_w_per_m * length, 1)
                lm_per_w = round(total_lumens / total_watts, 1) if total_watts > 0 else 0
                tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"

                file_name = f"{luminaire_name} {optic_name}_{length:.3f}m_{tier}"
                row = {
                    "Delete": "🗑️",
                    "Length (m)": f"{length:.3f}",
                    "Luminaire & IES File Name": file_name,
                    "CRI": cri,
                    "CCT": cct,
                    "Total Lumens": total_lumens,
                    "Total Watts": total_watts,
                    "Settings lm/W": lm_per_w,
                    "Comments": st.session_state['efficiency_reason']
                }
                table_rows.append(row)

            # === TABLE DISPLAY ===
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

                row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                            row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]

                for col, val in zip(cols[1:], row_data):
                    col.write(val)

            # === CSV EXPORT ===
            df_export = pd.DataFrame([{
                "Length (m)": r["Length (m)"],
                "Luminaire & IES File Name": r["Luminaire & IES File Name"],
                "CRI": r["CRI"],
                "CCT": r["CCT"],
                "Total Lumens": r["Total Lumens"],
                "Total Watts": r["Total Watts"],
                "Settings lm/W": r["Settings lm/W"],
                "Comments": r["Comments"]
            } for r in table_rows])

            st.download_button("📥 Download CSV Summary", data=df_export.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

        else:
            st.info("No lengths selected yet.")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        difference = round((achieved_lux - target_lux) / target_lux * 100, 1) if target_lux > 0 else 0
        st.write(f"Difference: {difference}%")

        required_change = round(base_lm_per_m * abs(difference) / 100, 1)
        increments_needed = int(required_change // st.session_state['lmw_step_increment'])

        if difference > 0:
            if increments_needed < 1:
                st.warning("⚠️ Dimming recommended to match target lux.")
            else:
                st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming.")
        elif difference < 0:
            if increments_needed < 1:
                st.warning("⚠️ Consider increasing output or switching to a higher spec IES file.")
            else:
                st.warning(f"⚠️ Consider increasing by {increments_needed} increments.")

        st.info("Note: This enables theoretical model accuracy for future optimisations.")

    # === IES FILE GENERATION PLACEHOLDER ===
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")

else:
    st.info("Upload an IES file to begin.")
