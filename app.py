# === Base Build Methodology (Expander with Toggle Lock) ===
with st.expander("📂 Base Build Methodology", expanded=False):
    
    # Initialize session state on first run
    if 'locked' not in st.session_state:
        st.session_state['locked'] = False
        st.session_state['lengths_list'] = []
        st.session_state['end_plate_thickness'] = 5.5
        st.session_state['led_pitch'] = 56.0

    # Toggle Button Logic: Lock/Unlock
    if st.session_state['locked']:
        if st.button("🔓 Unlock Base Build Methodology"):
            st.session_state['locked'] = False
    else:
        if st.button("🔒 Lock Base Build Methodology"):
            st.session_state['locked'] = True

    # === If Unlocked ===
    if not st.session_state['locked']:
        st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
        
        # Editable fields when unlocked
        end_plate_thickness = st.number_input(
            "End Plate Expansion Gutter (mm)", 
            min_value=0.0, 
            value=st.session_state['end_plate_thickness'], 
            step=0.1
        )

        led_pitch = st.number_input(
            "LED Series Module Pitch (mm)", 
            min_value=14.0,  # ✅ New min value
            value=st.session_state['led_pitch'], 
            step=0.1
        )

        # Save values into session state on lock
        if st.session_state['locked']:
            st.session_state['end_plate_thickness'] = end_plate_thickness
            st.session_state['led_pitch'] = led_pitch

    # === If Locked ===
    else:
        end_plate_thickness = st.session_state['end_plate_thickness']
        led_pitch = st.session_state['led_pitch']

        st.info(f"🔒 Locked: End Plate Expansion Gutter = {end_plate_thickness} mm | LED Series Module Pitch = {led_pitch} mm")
