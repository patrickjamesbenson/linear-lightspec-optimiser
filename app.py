# === DESIGN OPTIMISATION SECTION ===
with st.expander("🎯 Design Optimisation", expanded=False):
    st.subheader("Target vs Achieved Lux Levels")

    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=700.0, step=1.0)

    if target_lux == 0:
        st.error("Target Lux must be greater than 0.")
    else:
        difference_percent = round(((achieved_lux - target_lux) / target_lux) * 100, 1)

        st.markdown(f"**Difference:** {difference_percent:+.1f}%")

        # Calculate lm/m adjustments
        current_lm_per_m = 400.0  # Example placeholder, should link to actual current data
        required_adjustment = round(abs(current_lm_per_m * (difference_percent / 100.0)), 1)

        increments_needed = math.ceil(required_adjustment / 115)

        # Feedback logic
        if difference_percent > 0:
            st.warning(f"⚠️ Achieved lux is higher than target by {difference_percent:.1f}%.")
            st.info(f"Recommend reducing output by dimming **{abs(difference_percent):.1f}%** "
                    f"or selecting an IES file approximately **{increments_needed} increments lower** than the current.")
        elif difference_percent < 0:
            st.warning(f"⚠️ Achieved lux is lower than target by {abs(difference_percent):.1f}%.")
            st.info(f"Recommend increasing output by selecting an IES file approximately **{increments_needed} increments higher** "
                    f"than the current.")
        else:
            st.success("✅ Achieved lux matches target precisely.")

        # Upload Alternative IES File Section
        st.markdown("### Upload New Optimised IES File (optional)")
        alt_ies_file = st.file_uploader("Upload Alternative IES File", type=["ies"])

        # Precision Note
        st.markdown("""
        > 💡 *For future theoretical model optimisations, install and dim precisely to your simulation target.  
        On-site readings will show how close your modelling is to reality.*
        """)

