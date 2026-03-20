import streamlit as st


def render_settings_tab():
    """Render the settings tab with cache management options."""
    st.markdown("## Settings")
    
    st.markdown("### Cache Management")
    st.write("Cached items include market data, chart data, and computed calculations.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🗑️ Clear All Caches"):
            st.cache_data.clear()
            st.success("All caches cleared successfully!")
