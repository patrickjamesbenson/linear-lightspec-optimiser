# === LED CHIPSET ADJUSTMENT ===
with st.expander("LED Chipset Adjustment", expanded=True) as chipset_expander:
    # Show the input field for adjustment percentage
    led_chipset_adjustment = st.number_input(
        "LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=0.0, step=1.0,
        key="led_chipset_adjustment"
    )
    
    # Reason input
    reason = st.text_input(
        "Reason (e.g., Gen 2 LED +15% increase lumen output)",
        value=st.session_state.get('efficiency_reason', 'Current Generation'),
        key="led_chipset_reason"
    )
    
    # Validate if reason is required when adjustment ≠ 0
    if led_chipset_adjustment != 0 and reason.strip() == "":
        st.warning("Please enter a reason for the LED Chipset Adjustment before proceeding.")
        st.session_state['chipset_locked'] = False
    else:
        st.session_state['chipset_locked'] = True
        st.session_state['led_efficiency_gain_percent'] = led_chipset_adjustment
        st.session_state['efficiency_reason'] = reason
        st.session_state['efficiency_multiplier'] = 1 + (led_chipset_adjustment / 100)

# === FORCE LOCK AFTER CLOSING THE EXPANDER ===
if not chipset_expander:
    # Lock chipset adjustment and reason values when the expander is closed
    st.session_state['chipset_locked'] = True

# === SELECT LENGTHS TABLE: UPDATE DYNAMICALLY IF VALID ===
if st.session_state['chipset_locked']:
    # Ensure lengths_list exists
    if 'lengths_list' in st.session_state and st.session_state['lengths_list']:
        st.markdown("### Selected Lengths for IES Generation")

        base_lm_per_m = 400
        base_w_per_m = 20

        length_table_data = []

        efficiency_multiplier = st.session_state.get('efficiency_multiplier', 1)
        recommended_factor = st.session_state.get('recommended_factor', 1)
        reason = st.session_state.get('efficiency_reason', "Current Generation")

        for length in st.session_state['lengths_list']:
            lm_per_m = base_lm_per_m * recommended_factor * efficiency_multiplier
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
                "LED Chipset Adjustment": f"{efficiency_multiplier:.2f}",
                "LED Multiplier Reason": reason,
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
else:
    st.info("Awaiting valid LED Chipset Adjustment and Reason to proceed.")
