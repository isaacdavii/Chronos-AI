# For this new phase we need to use Python 3.11 (Open3D is not compatible with 3.13 yet). So, create a virtual environment specific for this version:
# Run:
# For Windows:
# py -3.11 -m venv .venv311
# .\.venv311\Scripts\activate  (Windows)
# For Linux/Mac:
# python3.11 -m venv .venv311
# source .venv311/bin/activate  (Linux/Mac)

# Then, install the dependencies:
# pip install -r requirements.txt

# Run the app:
# streamlit run App/app_en.py

# Deactivate the virtual environment after use:
# deactivate  (Linux/Mac/Windows)

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import plotly.express as px
import plotly.graph_objects as go
import laspy
import open3d as o3d
import tempfile
import os

# ===================
# PAGE CONFIGURATION
# ===================
st.set_page_config(
    page_title = "Chronos: AI Archaeology",
    layout = "wide",
    page_icon = "🏛️"
)


# =======
# HEADER
# =======
st.title("🏛️ Chronos - Computational Archaeology Platform")
st.markdown(
    "Advanced system for point cloud processing, anomaly detection (GPR), and volumetric artifact reconstruction."
)
st.markdown("---")


# =========================
# SIDEBAR: MODULE SELECTOR
# =========================
st.sidebar.title("Navigation")
modulo = st.sidebar.radio(
    "Choose Analysis Module:",
    ["1️⃣ Terrain Prospecting (DBSCAN)", "2️⃣ Artifact Reconstruction (Open3D)"],
)
st.sidebar.markdown("---")

# =========================================
# MODULE 1: ORIGINAL CODE (DBSCAN)
# =========================================
if modulo == "1️⃣ Terrain Prospecting (DBSCAN)":
    st.header("Module 1: Large Scale Structure Detection")

    st.sidebar.header("1. Data Configuration")
    uploaded_file = st.sidebar.file_uploader("Upload GPR File (CSV)", type = ["csv"])

    st.sidebar.header("2. AI Calibration (DBSCAN)")
    eps = st.sidebar.slider("Search Radius (Epsilon)", 0.5, 10.0, 3.0)
    min_samples = st.sidebar.slider("Minimum Density", 2, 20, 5)

    st.sidebar.header("3. Refinement")
    min_cluster_size = st.sidebar.slider(
        "Ignore Small Clusters (< Points)", 0, 100, 10
    )

    def generate_demo_data_wall():
        np.random.seed(42)
        N_NOISE, N_WALL = 1500, 500
        x_noise = np.random.uniform(0, 100, N_NOISE)
        y_noise = np.random.uniform(0, 100, N_NOISE)
        z_noise = np.random.uniform(-10, 0, N_NOISE)
        x_wall = np.linspace(10, 90, N_WALL)
        y_wall = (
            30
            + 0.4 * x_wall
            + 15 * np.sin(x_wall / 10)
            + np.random.normal(0, 1.0, N_WALL)
        )
        z_wall = np.random.normal(-3.0, 0.5, N_WALL)
        df_noise = pd.DataFrame(
            {"x": x_noise, "y": y_noise, "z": z_noise, "type": "Noise"}
        )
        df_wall = pd.DataFrame(
            {"x": x_wall, "y": y_wall, "z": z_wall, "type": "Real Wall"}
        )
        return pd.concat([df_noise, df_wall], ignore_index = True)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        st.info("💡 Displaying synthetic demo data (Hidden Wall).")
        df = generate_demo_data_wall()

    if st.sidebar.button("🔍 Start Scan", type = "primary"):
        with st.spinner("Processing point cloud with DBSCAN..."):
            model = DBSCAN(eps = eps, min_samples = min_samples)
            df["cluster"] = model.fit_predict(df[["x", "y", "z"]])

            counts = df["cluster"].value_counts()
            valid_clusters = counts[counts > min_cluster_size].index.tolist()
            df["filtered_cluster"] = df["cluster"].apply(
                lambda x: x if x in valid_clusters else -1
            )

            n_noise = len(df[df["filtered_cluster"] == -1])
            n_structure = len(df[df["filtered_cluster"] != -1])
            n_clusters = df["filtered_cluster"].nunique() - 1

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Analyzed Points", len(df))
            kpi2.metric("Discarded Noise", f"{n_noise} pts")
            kpi3.metric(
                "Confirmed Structure",
                f"{n_structure} pts",
                delta = f"{n_clusters} Clusters",
            )

            df["Legend"] = df["filtered_cluster"].apply(
                lambda x: "Soil Noise" if x == -1 else f"Structure #{x}"
            )

            tab1, tab2 = st.tabs(["🌍 Interactive 3D View", "🗺️ Floor Plan (2D)"])
            with tab1:
                fig_3d = px.scatter_3d(
                    df,
                    x = "x",
                    y = "y",
                    z = "z",
                    color = "Legend",
                    color_discrete_map = {"Soil Noise": "lightgray"},
                    height = 600,
                )
                fig_3d.update_traces(marker = dict(size = 3))
                st.plotly_chart(fig_3d, use_container_width = True)
            with tab2:
                df_map = df[df["filtered_cluster"] != -1]
                if not df_map.empty:
                    fig_2d = px.scatter(
                        df_map, 
                        x = "x",
                        y = "y",
                        color = "Legend",
                        height = 600
                    )
                    fig_2d.update_yaxes(scaleanchor = "x", scaleratio = 1)
                    st.plotly_chart(fig_2d, use_container_width = True)
            
            st.markdown("---")
            st.subheader("💾 Data Export")
            
            # Convert the cleaned DataFrame (without noise) to CSV
            csv = df_map.to_csv(index = False).encode('utf-8')
            
            st.download_button(
                label = "📥 Download Vector Plan (.csv)",
                data = csv,
                file_name = "chronos_archaeological_plan.csv",
                mime = "text/csv"
            )

# ======================================
# MODULE 2: NEW CODE (OPEN3D / POISSON)
# ======================================
elif modulo == "2️⃣ Artifact Reconstruction (Open3D)":
    if o3d is None:
        st.error(
            "⚠️ The Open3D library is not installed or is incompatible with your Python version (3.13). Please use Python 3.10 or 3.11 to access this module."
        )
        st.stop()

    st.header("Module 2: Micro-Excavation and 3D Reconstruction")

    st.sidebar.header("1. Data Input")
    data_source = st.sidebar.selectbox(
        "Data Source:",
        ["Simulation: Amphora with Noise", "Upload LIDAR File (.las)"],
    )
    las_file = None
    if data_source == "Upload LIDAR File (.las)":
        las_file = st.sidebar.file_uploader(
            "Upload LIDAR (.las / .laz)", type = ["las", "laz"]
        )

    st.sidebar.header("2. Digital Cleaning")
    nb_neighbors = st.sidebar.slider(
        "Filter: Neighbors",
        10,
        100,
        50,
        help = "How many neighbors a point needs to have to not be considered dust.",
    )
    std_ratio = st.sidebar.slider(
        "Filter: Strictness", 0.1, 3.0, 1.0, help = "Lower = More strict cleaning."
    )
    st.sidebar.markdown("---")
    use_ransac = st.sidebar.checkbox("Enable Ground Removal (RANSAC)", value = False, help = "Removes the terrain to isolate ruins.")
    ransac_dist = st.sidebar.slider("Ground Tolerance (m)", 0.1, 2.0, 0.5, help = "Increase if the ground is very irregular (hills).")

    st.sidebar.header("3. Meshing (Surface)")
    poisson_depth = st.sidebar.slider(
        "Mesh Resolution",
        6,
        10,
        8,
        help = "Higher = More details, but requires more processing power.",
    )

    # Function to generate synthetic amphora
    @st.cache_data
    def generate_dirty_amphora():
        np.random.seed(42)
        points_artifact, points_noise = [], []
        height_layers = 60
        for z_idx in range(height_layers):
            z = (z_idx / height_layers) * 10
            if z < 1.0:
                r = 2.0 + (z * 0.5)
            elif z < 6.0:
                r = 2.5 + 1.5 * np.sin((z - 1) * 0.8)
            elif z < 8.0:
                r = 1.5 + 0.5 * np.cos((z - 6) * 1.5)
            else:
                r = 2.0 + (z - 8) * 0.5
            if np.random.random() > 0.3:
                for i in range(50):
                    theta = (i / 50) * 2 * np.pi
                    noise = np.random.normal(0, 0.15)
                    points_artifact.append(
                        [(r + noise) * np.cos(theta), (r + noise) * np.sin(theta), z]
                    )
        for _ in range(8000):
            points_noise.append(
                [
                    np.random.uniform(-5, 5),
                    np.random.uniform(-5, 5),
                    np.random.uniform(-2, 12),
                ]
            )
        all_points = np.vstack((points_artifact, points_noise))
        np.random.shuffle(all_points)
        return all_points

    # Prepare points based on user choice
    raw_points = None
    if data_source == "Simulation: Amphora with Noise":
        st.info(
            "💡 Using synthetic scan of a highly noisy ceramic artifact (Amphora)."
        )
        raw_points = generate_dirty_amphora()
    elif las_file is not None:
        with st.spinner("Reading LIDAR file and applying Voxel Downsampling..."):
            las = laspy.read(las_file)
            real_points = np.vstack((las.x, las.y, las.z)).transpose()
            # Automatic Voxel Downsampling to prevent freezing
            pcd_temp = o3d.geometry.PointCloud()
            pcd_temp.points = o3d.utility.Vector3dVector(real_points)
            pcd_down = pcd_temp.voxel_down_sample(voxel_size = 0.05)  # 5cm Voxel
            raw_points = np.asarray(pcd_down.points)
            st.success(
                f"LIDAR loaded and optimized! (From {len(real_points)} to {len(raw_points)} points)."
            )

    if (
        st.sidebar.button("⚙️ Start Reconstruction", type = "primary")
        and raw_points is not None
    ):

        # 1. Statistical Outlier Removal
        with st.spinner(
            "Step 1: Removing sand and debris (Statistical Outlier Removal)..."
        ):
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(raw_points)
            pcd_clean, ind = pcd.remove_statistical_outlier(
                nb_neighbors = nb_neighbors, std_ratio = std_ratio
            )
            pcd_clean = pcd.select_by_index(ind)
            
            if use_ransac:
                with st.spinner("Step 1.5: Blasting topographic ground (RANSAC)..."):
                    # segment_plane finds the floor. 'invert=True' keeps everything that IS NOT the floor.
                    plane_model, inliers = pcd_clean.segment_plane(distance_threshold = ransac_dist,
                                                                   ransac_n = 3,
                                                                   num_iterations = 1000)
                    pcd_clean = pcd_clean.select_by_index(inliers, invert = True)
            
            clean_points = np.asarray(pcd_clean.points)

        # 2. Poisson Reconstruction
        with st.spinner(
            "Step 2: Calculating normals and weaving solid mesh (Poisson Reconstruction)..."
        ):
            pcd_clean.estimate_normals(
                search_param = o3d.geometry.KDTreeSearchParamHybrid(radius = 1.0, max_nn = 30)
            )
            pcd_clean.orient_normals_consistent_tangent_plane(k = 20)
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                pcd_clean, depth = poisson_depth
            )

            # Trim Poisson excess
            densities = np.asarray(densities)
            vertices_to_remove = densities < np.quantile(densities, 0.05)
            mesh.remove_vertices_by_mask(vertices_to_remove)

            verts = np.asarray(mesh.vertices)
            tris = np.asarray(mesh.triangles)

        # 3. Metrology
        with st.spinner("Step 3: Calculating discovery dimensions..."):
            bbox = pcd_clean.get_axis_aligned_bounding_box()
            min_b, max_b = bbox.get_min_bound(), bbox.get_max_bound()
            dim_x, dim_y, dim_z = (
                max_b[0] - min_b[0],
                max_b[1] - min_b[1],
                max_b[2] - min_b[2],
            )
            volume_box = dim_x * dim_y * dim_z

        # RESULTS DISPLAY
        st.subheader("Digital Excavation Results")

        # Metrological KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Width (X)", f"{dim_x:.2f} m")
        col2.metric("Depth (Y)", f"{dim_y:.2f} m")
        col3.metric("Height (Z)", f"{dim_z:.2f} m")
        col4.metric("Occupancy Volume", f"{volume_box:.2f} m³")

        tabA, tabB = st.tabs(
            ["✨ Reconstructed Artifact (3D Mesh)", "🧹 Clean Point Cloud"]
        )

        with tabA:
            # Golden Solid Object Graph
            fig_mesh = go.Figure(
                data=[
                    go.Mesh3d(
                        x = verts[:, 0],
                        y = verts[:, 1],
                        z = verts[:, 2],
                        i = tris[:, 0],
                        j = tris[:, 1],
                        k = tris[:, 2],
                        color = "#B8860B",
                        opacity = 1.0,
                        flatshading = False,
                        lighting = dict(
                            ambient = 0.4, diffuse = 0.6, roughness = 0.1, specular = 0.3
                        ),
                        name = "Artifact",
                    )
                ]
            )
            fig_mesh.update_layout(
                scene = dict(aspectmode = "data", bgcolor = "black"),
                paper_bgcolor = "black",
                height = 600,
                margin = dict(l = 0, r = 0, b = 0, t = 0),
            )
            st.plotly_chart(fig_mesh, use_container_width = True)

        with tabB:
            # Comparative Before/After Graph
            fig_pts = go.Figure()
            # Original noise (in opaque red and small)
            fig_pts.add_trace(
                go.Scatter3d(
                    x = raw_points[:, 0],
                    y = raw_points[:, 1],
                    z = raw_points[:, 2],
                    mode = "markers",
                    marker = dict(size = 1, color = "red", opacity = 0.1),
                    name = "Original Chaos",
                )
            )
            # Clean Points (in gold)
            fig_pts.add_trace(
                go.Scatter3d(
                    x = clean_points[:, 0],
                    y = clean_points[:, 1],
                    z = clean_points[:, 2],
                    mode = "markers",
                    marker = dict(size = 3, color = "gold", opacity = 0.8),
                    name = "Filtered Signal",
                )
            )
            fig_pts.update_layout(
                scene = dict(aspectmode = "data", bgcolor = "black"),
                paper_bgcolor = "black",
                height = 600,
                margin = dict(l = 0, r = 0, b = 0, t = 0),
            )
            st.plotly_chart(fig_pts, use_container_width = True)
    
        # Data Export
        st.markdown("---")
        st.subheader("💾 Data Export")

        with tempfile.NamedTemporaryFile(delete = False, suffix = ".obj") as tmp:
            tmp_name = tmp.name
        
        o3d.io.write_triangle_mesh(tmp_name, mesh)
        with open(tmp_name, "rb") as f:
            obj_data = f.read()
            
        os.unlink(tmp_name)  # Clean up the temporary file from the server's memory

        st.download_button(
            label = "📥 Download Digital Twin (.obj)",
            data = obj_data,
            file_name = "chronos_reconstructed_artifact.obj",
            mime = "application/octet-stream"
        )