# --- History Section ---
if st.session_state.history:
    st.markdown("---")
    with st.expander("Recent translations"):
        for english, gujarati, engine in st.session_state.history:
            st.markdown(f"**English:** {english}")
            st.markdown(f"**ગુજરાતી:** {gujarati} *(via {engine})*")
            st.divider()

st.caption("Powered by Sarvam AI · Made with ❤️ for Gujarati STEM Education")
