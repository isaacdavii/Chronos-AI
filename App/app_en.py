# If you need to, create a virtual environment, run the appropriate command:
# source .venv/bin/activate  (Linux/Mac)
# .\venv\Scripts\activate (Windows)
# Then, install the dependencies:
# pip install streamlit pandas scikit-learn plotly
# Run the app:
# streamlit run App/app_en.py

# Deactivate the virtual environment after use:
# deactivate  (Linux/Mac/Windows)

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title = "Chronos: AI Archaeology",
    layout = "wide",
    page_icon = "🏛️"
)

# --- HEADER ---
st.title("🏛️ Chronos - Archaeological Detection System")
st.markdown("""
**Transform raw radar data into historical discoveries.**
This system uses the *DBSCAN* algorithm to separate geological noise from buried architectural structures.
""")
st.markdown("---")

# --- SIDEBAR (CONTROLS) ---
st.sidebar.header("1. Data Configuration")
uploaded_file = st.sidebar.file_uploader("Upload GPR File (CSV)", type = ["csv"])

st.sidebar.header("2. AI Calibration (DBSCAN)")
eps = st.sidebar.slider("Search Radius (Epsilon)", 0.5, 10.0, 3.0, help = "Maximum distance between two points to be considered neighbors.")
min_samples = st.sidebar.slider("Minimum Density", 2, 20, 5, help = "Minimum points to form an initial cluster.")

st.sidebar.header("3. Refinement (Post-Processing)")
min_cluster_size = st.sidebar.slider("Ignore Small Clusters (< Points)", 0, 100, 10, help = "Removes small debris detected as structure.")

# --- DEMO DATA FUNCTION ---
def generate_demo_data():
    # Procedural generation of a "Curved Wall and Noise" (synthetic data for demo)
    np.random.seed(42) # Seed for reproducibility
    N_NOISE = 1500
    N_WALL = 500
    
    # Scattered noise
    x_noise = np.random.uniform(0, 100, N_NOISE)
    y_noise = np.random.uniform(0, 100, N_NOISE)
    z_noise = np.random.uniform(-10, 0, N_NOISE)
    
    # Structure (Sine wave with thickness)
    x_wall = np.linspace(10, 90, N_WALL)
    y_wall = 30 + 0.4 * x_wall + 15 * np.sin(x_wall / 10) + np.random.normal(0, 1.0, N_WALL)
    z_wall = np.random.normal(-3.0, 0.5, N_WALL) # Wall is at 3m depth
    
    df_noise = pd.DataFrame({'x': x_noise, 'y': y_noise, 'z': z_noise, 'type': 'Noise'})
    df_wall = pd.DataFrame({'x': x_wall, 'y': y_wall, 'z': z_wall, 'type': 'Real Wall'})
    
    return pd.concat([df_noise, df_wall], ignore_index=True)

# --- LOAD DATA ---
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    # Show warning only on first load
    st.sidebar.info("💡 Tip: Using synthetic demo data.")
    df = generate_demo_data()

# --- MAIN PROCESSING ---
# Main action button
if st.sidebar.button("🔍 Start Scan", type = "primary"):
    
    with st.spinner('Processing point cloud...'):
        # 1. Apply DBSCAN
        model = DBSCAN(eps = eps, min_samples = min_samples)
        clusters = model.fit_predict(df[['x', 'y', 'z']])
        df['cluster'] = clusters

        # 2. Heuristic Filter (Logic)
        # Count points in each cluster
        counts = df['cluster'].value_counts()
        
        # Create list of valid clusters (larger than slider filter)
        # Cluster -1 (noise) is kept separate
        valid_clusters = counts[counts > min_cluster_size].index.tolist()
        
        # If cluster is too small, it becomes noise (-1)
        df['filtered_cluster'] = df['cluster'].apply(lambda x: x if x in valid_clusters else -1)

        # 3. Statistics
        n_noise = len(df[df['filtered_cluster'] == -1])
        n_structure = len(df[df['filtered_cluster'] != -1])
        n_clusters = df['filtered_cluster'].nunique() - 1 # Remove -1 from count

        # Display Metrics at Top
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Analyzed Points", len(df))
        kpi2.metric("Discarded Noise", f"{n_noise} pts", delta = "-Rejected", delta_color = "inverse")
        kpi3.metric("Confirmed Structure", f"{n_structure} pts", delta = f"{n_clusters} Clusters", delta_color = "normal")

        # --- VISUALIZATION ---
        
        # Prepare nice legend
        df['Legend'] = df['filtered_cluster'].apply(lambda x: 'Soil Noise' if x == -1 else f'Structure #{x}')
        
        # TABS for 3D and 2D
        tab1, tab2 = st.tabs(["🌍 Interactive 3D View", "🗺️ Floor Plan (2D)"])
        
        with tab1:
            fig_3d = px.scatter_3d(
                df, x = 'x', y = 'y', z = 'z', 
                color = 'Legend',
                color_discrete_map = {'Soil Noise': 'lightgray'},
                opacity = 0.7,
                height = 600,
                title = "Volumetric Terrain Model"
            )
            fig_3d.update_traces(marker = dict(size = 3)) # Smaller points look sleeker
            st.plotly_chart(fig_3d, use_container_width = True)

        with tab2:
            # Filter only structure for clean map
            df_map = df[df['filtered_cluster'] != -1]
            
            if not df_map.empty:
                fig_2d = px.scatter(
                    df_map, x = 'x', y = 'y',
                    color = 'Legend',
                    height = 600,
                    title = "Top Projection (Excavation Plan)"
                )
                fig_2d.update_yaxes(scaleanchor = "x", scaleratio = 1) # Keep real 1:1 aspect ratio
                st.plotly_chart(fig_2d, use_container_width = True)
            else:
                st.warning("No structure found with these parameters. Try increasing Epsilon or decreasing Density.")

        # --- DOWNLOAD ---
        st.markdown("### 📥 Export Data")
        csv = df[df['filtered_cluster'] != -1].to_csv(index = False).encode('utf-8')
        st.download_button(
            label = "Download Vector Report (CSV)",
            data = csv,
            file_name = "chronos_detected.csv",
            mime = "text/csv"
        )

else:

    st.info("👈 Adjust parameters in the sidebar and click 'Start Scan'.")
