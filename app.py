import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INIT ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0
if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = "Current Generation"
if 'lmw_increment' not in st.session_state:
    st.session_state['lmw_increment'] = 115.0
if 'export_id' not in st.session_state:
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT METADATA ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

    cri_value = "N/A"
    cct_value = "N/A"

    parts = luminaire_name_base.split('-')
    if len(parts) >= 4:
        cri_value = parts[-2].strip()
        cct_value = parts[-1].strip()

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        ies_version = next((line for line in parsed['header'] if line.startswith("IESNA")), "Not Found")
        test_info = next((line for line in parsed['header'] if line.startswith("[TEST]")), "[TEST] Not Found")
        manufac_info = next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "[MANUFAC] Not Found")
        lumcat_info = next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "[LUMCAT] Not Found")
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
            st.info(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.subheader("Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")

    if st.button("Add Length"):
        st.session_state['lengths_list'].append(desired_length_m)
        st.session_state['locked'] = True
        st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_eff = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'])
        reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

        if led_eff != 0 and reason.strip() == "":
            st.error("You must provide a reason when adjusting LED chipset efficiency!")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_eff
        st.session_state['efficiency_reason'] = reason

    # === lm/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.
        For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_increment']:.1f} lm/W")
        else:
            st.session_state['lmw_increment'] = st.number_input("Average lm/W Step Increment", min_value=10.0, max_value=500.0, value=115.0)

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        table_rows = []
        base_lm_per_m = 400.0
        base_w_per_m = 11.6

        efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
            luminaire_file_name = f"{luminaire_name_base}_{length:.3f}m_{tier}"

            row = {
                "Delete": "🗑️",
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": reason if st.session_state['led_efficiency_gain_percent'] != 0 else ""
            }

            table_rows.append(row)

        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for idx, row in enumerate(table_rows):
            row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
            if row_cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if not st.session_state['lengths_list']:
                    st.session_state['locked'] = False
                st.rerun()

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                        row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]
            for col, val in zip(row_cols[1:], row_data):
                col.write(val)

        export_df = pd.DataFrame([{
            "Length (m)": r["Length (m)"],
            "Luminaire & IES File Name": r["Luminaire & IES File Name"],
            "CRI": r["CRI"],
            "CCT": r["CCT"],
            "Total Lumens": r["Total Lumens"],
            "Total Watts": r["Total Watts"],
            "Settings lm/W": r["Settings lm/W"],
            "Comments": r["Comments"]
        } for r in table_rows])

        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    else:
        st.info("No lengths selected yet. Add lengths to generate table.")

    # === DESIGN OPTIMISATION ===
    st.markdown("## 🎯 Design Optimisation")
    with st.expander("Design Optimisation", expanded=False):
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=10.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=10.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = max(1, int(required_change_lm_per_m // st.session_state['lmw_increment']))

        if difference_percent > 0:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
        elif difference_percent < 0:
            st.success(f"✅ Consider increasing by {increments_needed} increments or boosting output.")
        else:
            st.info("🎯 Target achieved! Fine-tune dimming for optimal results.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE IES FILES ===
    st.markdown("## Generate Optimised IES Files")

    if st.button("Generate IES Files & Download ZIP"):
        files_to_zip = {}
        for length in st.session_state['lengths_list']:
            scaled_data = modify_candela_data(parsed['data'], 1.0)

            updated_header = []
            for line in parsed['header']:
                if line.startswith("[TEST]"):
                    updated_header.append(f"[TEST] Export ID: {st.session_state['export_id']}")
                else:
                    updated_header.append(line)

            new_file = create_ies_file(updated_header, scaled_data)
            filename = f"{luminaire_name_base}_{length:.3f}m.ies"
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button("Download Optimised IES Files (ZIP)", data=zip_buffer, file_name="Optimised_IES_Files.zip", mime="application/zip")

else:
    st.info("Upload an IES file to begin optimisation.")
