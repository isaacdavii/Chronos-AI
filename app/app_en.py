"""
Chronos — Computational Archaeology Platform (English interface).

Run with:
    pip install -r requirements.txt
    streamlit run app/app_en.py

All logic lives in `chronos_core.py`, shared with `app_pt.py`. This file only
translates and draws.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import chronos_core as core

# Core returns language-neutral codes; the UI turns them into sentences.
WARNINGS = {
    "RANSAC_ALL_GROUND": "RANSAC classified the whole cloud as ground; the step "
                         "was skipped.",
    "DBSCAN_CLUSTER_TINY": "The largest coherent cluster is tiny; density "
                           "detection was skipped.",
    "DBSCAN_NO_CLUSTER": "DBSCAN found no coherent cluster; the step was skipped.",
    "NORMALS_FLIPPED": "Normals were pointing inwards; orientation was corrected "
                       "automatically.",
    "MESH_NOT_WATERTIGHT": "The mesh is not watertight — density pruning opens "
                           "holes by construction. True volume is undefined; use "
                           "the envelope instead.",
}

ERRORS = {
    "EMPTY_FILE": "The file is empty.",
    "NON_NUMERIC_COLUMNS": "Columns x, y and z must be numeric.",
    "EMPTY_MESH": "Poisson produced an empty mesh. Lower the resolution.",
}


def describe_error(code: str) -> str:
    """Map a core error code to a readable sentence."""
    head, _, detail = code.partition(":")
    if head == "MISSING_COLUMNS":
        return f"missing columns: {detail}"
    if head == "NULL_ROWS":
        return f"{detail} rows contain null values"
    if head == "TOO_FEW_POINTS":
        return (f"only {detail} points survived filtering. Loosen the filter "
                "strictness.")
    return ERRORS.get(head, code)


st.set_page_config(page_title="Chronos: AI for Archaeology",
                   layout="wide",
                   page_icon="🏛️")


def chart(fig, **kw):
    """`width='stretch'` is the recent API, `use_container_width` the older one."""
    try:
        st.plotly_chart(fig, width="stretch", **kw)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, **kw)


st.title("🏛️ Chronos — Computational Archaeology Platform")
st.caption("Point cloud processing, anomaly detection and volumetric artifact "
           "reconstruction.")
st.divider()

st.sidebar.title("Navigation")
module = st.sidebar.radio("Analysis module:",
                          ["1️⃣ Terrain Prospecting (DBSCAN)",
                           "2️⃣ Artifact Reconstruction (Open3D)"])
st.sidebar.divider()

# =========================================================================== #
# MODULE 1
# =========================================================================== #
if module.startswith("1"):
    st.header("Module 1 — Large-scale structure detection")

    st.sidebar.header("1. Data")
    uploaded = st.sidebar.file_uploader("GPR file (CSV with x, y, z)",
                                        type=["csv"])

    @st.cache_data
    def demo_wall(seed: int = 42) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        n_noise, n_wall = 1500, 500
        noise = pd.DataFrame({"x": rng.uniform(0, 100, n_noise),
                              "y": rng.uniform(0, 100, n_noise),
                              "z": rng.uniform(-10, 0, n_noise)})
        xs = np.linspace(10, 90, n_wall)
        wall = pd.DataFrame({
            "x": xs,
            "y": 30 + 0.4 * xs + 15 * np.sin(xs / 10) + rng.normal(0, 1.0, n_wall),
            "z": rng.normal(-3.0, 0.5, n_wall),
        })
        return pd.concat([noise, wall], ignore_index=True)

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"Could not read the CSV: {exc}")
            st.stop()

        valid, reason = core.validate_dataframe(df)
        if not valid:
            st.error(f"Invalid file — {describe_error(reason)}. The CSV needs "
                     "numeric `x`, `y` and `z` columns.")
            st.stop()
        st.success(f"{len(df):,} points loaded.")
    else:
        st.info("Showing synthetic demo data (hidden wall).")
        df = demo_wall()

    st.sidebar.header("2. DBSCAN calibration")
    if st.sidebar.button("📐 Suggest epsilon"):
        st.session_state["eps_hint"] = core.suggest_eps(df)

    default_eps = float(st.session_state.get("eps_hint", 3.0))
    if "eps_hint" in st.session_state:
        st.sidebar.caption(f"k-distance knee: {default_eps:.2f}")

    with st.sidebar.form("form_prospecting"):
        eps = st.slider("Search radius (epsilon)", 0.5, 10.0,
                        min(max(default_eps, 0.5), 10.0), 0.1)
        min_samples = st.slider("Minimum density", 2, 20, 5)
        min_size = st.slider("Ignore clusters with fewer than N points",
                             0, 100, 10)
        run = st.form_submit_button("🔍 Start scan", type="primary")

    if run:
        with st.spinner("Processing point cloud…"):
            st.session_state["prospecting_result"] = core.prospect(
                df, eps, min_samples, min_size)

    # Reading from session_state keeps results alive across widget reruns.
    result = st.session_state.get("prospecting_result")
    if result is not None:
        d = result.df

        k1, k2, k3 = st.columns(3)
        k1.metric("Points analysed", f"{len(d):,}")
        k2.metric("Noise discarded", f"{result.n_noise:,}")
        k3.metric("Structure confirmed", f"{result.n_structure:,}",
                  delta=f"{result.n_clusters} clusters")

        if result.n_clusters == 0:
            st.warning("No cluster passed the filters. Increase epsilon or "
                       "lower the minimum density.")
        else:
            d["Legend"] = np.where(
                d["cluster_filtered"] == -1, "Soil noise",
                "Structure #" + d["cluster_filtered"].astype(str))

            t1, t2 = st.tabs(["🌍 3D view", "🗺️ Floor plan"])
            with t1:
                fig = px.scatter_3d(d,
                                    x="x",
                                    y="y",
                                    z="z",
                                    color="Legend",
                                    color_discrete_map={"Soil noise": "lightgray"},
                                    height=600)
                fig.update_traces(marker=dict(size=3))
                chart(fig)

            plan = d[d["cluster_filtered"] != -1]
            with t2:
                fig = px.scatter(plan,
                                 x="x",
                                 y="y",
                                 color="Legend",
                                 height=600)
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                chart(fig)

            st.divider()
            st.subheader("💾 Export")
            st.download_button("📥 Vector plan (.csv)",
                               plan.to_csv(index=False).encode("utf-8"),
                               "chronos_archaeological_plan.csv",
                               "text/csv")
            st.caption("Precise site coordinates enable looting. Consider "
                       "generalising locations before publishing, and check the "
                       "legal regime in your jurisdiction — in Brazil sites are "
                       "federal property (Lei 3.924/1961) and survey requires "
                       "IPHAN authorisation.")

# =========================================================================== #
# MODULE 2
# =========================================================================== #
else:
    if not core.HAS_OPEN3D:
        st.error(f"Open3D is unavailable here.\n\n`{core.OPEN3D_ERROR}`\n\n"
                 "Open3D 0.19 ships wheels for Python 3.8–3.12 only. Install it "
                 "with `pip install open3d` in a compatible environment.")
        st.stop()

    st.header("Module 2 — Micro-excavation and 3D reconstruction")

    st.sidebar.header("1. Input")
    source = st.sidebar.selectbox("Data source:",
                                  ["Simulation: noisy amphora",
                                   "Upload LIDAR (.las / .laz)"])
    las_file = None
    if source.startswith("Upload"):
        las_file = st.sidebar.file_uploader("LIDAR", type=["las", "laz"])

    with st.sidebar.form("form_reconstruction"):
        st.subheader("2. Cleaning")
        nb_neighbors = st.slider("Filter: neighbours", 10, 100, 50)
        std_ratio = st.slider("Filter: strictness", 0.1, 3.0, 1.0, 0.1,
                              help="Lower is more aggressive.")
        use_dbscan = st.checkbox(
            "Isolate largest coherent structure (DBSCAN)", value=True,
            help="Detects the artifact before reconstructing. Without it "
                 "Poisson models the noise envelope instead of the object.")
        use_ransac = st.checkbox("Remove ground (RANSAC)", value=False)
        ransac_dist = st.slider("Ground tolerance", 0.1, 2.0, 0.5, 0.1)

        st.subheader("3. Meshing")
        poisson_depth = st.slider("Resolution (Poisson depth)", 6, 10, 8)
        prune_quantile = st.slider("Density pruning (quantile)",
                                   0.0, 0.30, 0.05, 0.01)
        run = st.form_submit_button("⚙️ Start reconstruction", type="primary")

    points = None
    if source.startswith("Simulation"):
        st.info("Synthetic scan of a ceramic amphora with volumetric noise.")
        points = core.generate_amphora(seed=42)
    elif las_file is not None:
        with st.spinner("Reading LIDAR…"):
            points, meta = core.load_las(las_file)
        st.success(f"{meta['n_raw']:,} → {meta['n_final']:,} points "
                   f"(adaptive voxel of {meta['voxel']:.3f}).")
        if meta["crs"] is None:
            st.warning("The file declares no coordinate reference system (CRS). "
                       "Without one the cloud cannot be combined with other data.")

    if run and points is not None:
        try:
            with st.spinner("SOR → detection → Poisson → metrology…"):
                st.session_state["reconstruction_result"] = core.reconstruct(
                    points,
                    nb_neighbors=nb_neighbors,
                    std_ratio=std_ratio,
                    use_ransac=use_ransac,
                    ransac_dist=ransac_dist,
                    use_dbscan=use_dbscan,
                    poisson_depth=poisson_depth,
                    prune_quantile=prune_quantile)
        except ValueError as exc:
            st.error(f"Reconstruction failed: {describe_error(str(exc))}")
            st.session_state.pop("reconstruction_result", None)
        except Exception as exc:
            st.error(f"Reconstruction failed: {exc}")
            st.session_state.pop("reconstruction_result", None)
    elif run:
        st.warning("Load a file before reconstructing.")

    result = st.session_state.get("reconstruction_result")
    if result is not None:
        for code in result.warnings:
            st.warning(WARNINGS.get(code, code))

        st.subheader("Results")
        met, quality = result.metrology, result.quality

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Width (X)", f"{met['width']:.2f}")
        c2.metric("Depth (Y)", f"{met['depth']:.2f}")
        c3.metric("Height (Z)", f"{met['height']:.2f}")
        c4.metric("True volume",
                  f"{met['volume_true']:.2f}" if met["volume_true"] else "undefined")
        st.caption("Units follow the input file. A georeferenced `.las` carries "
                   "metres; the simulation is dimensionless.")

        with st.expander("📐 Detailed volumetry and mesh quality"):
            v1, v2 = st.columns(2)
            with v1:
                st.markdown("**Volumes** (largest envelope to true volume)")
                st.write({
                    "AABB envelope": round(met["volume_aabb"], 3),
                    "Oriented envelope (OBB)":
                        round(met["volume_obb"], 3) if met["volume_obb"] else None,
                    "Convex hull":
                        round(met["volume_hull"], 3) if met["volume_hull"] else None,
                    "True volume (mesh)":
                        round(met["volume_true"], 3) if met["volume_true"]
                        else "requires a watertight mesh",
                    "Convexity (true/hull)":
                        round(met["convexity"], 3) if met["convexity"] else None,
                })
            with v2:
                st.markdown("**Topology**")
                st.write({
                    "Watertight": quality["watertight"],
                    "Edge-manifold": quality["edge_manifold"],
                    "Vertex-manifold": quality["vertex_manifold"],
                    "Orientable": quality["orientable"],
                    "No self-intersection": not quality["self_intersecting"],
                    "Vertices": quality["n_vertices"],
                    "Triangles": quality["n_triangles"],
                })

        if met["volume_hull"]:
            with st.expander("⚖️ Mass under each material hypothesis"):
                st.dataframe(core.mass_scenarios(met["volume_hull"]).round(2),
                             hide_index=True)
                st.caption("The hull volume is an upper bound on occupied space, "
                           "not a quantity of matter. GPR measures dielectric "
                           "contrast, not composition — the material is the "
                           "operator's hypothesis and requires XRF or direct "
                           "analysis to confirm.")

        verts = np.asarray(result.mesh.vertices)
        tris = np.asarray(result.mesh.triangles)
        ta, tb, tc = st.tabs(["✨ Reconstructed artifact", "🧹 Filtered cloud",
                              "📊 Confidence map"])

        scene = dict(scene=dict(aspectmode="data", bgcolor="black"),
                     paper_bgcolor="black",
                     height=600,
                     margin=dict(l=0, r=0, b=0, t=0))

        with ta:
            fig = go.Figure(go.Mesh3d(
                x=verts[:, 0],
                y=verts[:, 1],
                z=verts[:, 2],
                i=tris[:, 0],
                j=tris[:, 1],
                k=tris[:, 2],
                color="#B8860B",
                opacity=1.0,
                flatshading=False,
                lighting=dict(ambient=0.4,
                              diffuse=0.6,
                              roughness=0.1,
                              specular=0.3)))
            fig.update_layout(**scene)
            chart(fig)

        with tb:
            fig = go.Figure()
            fig.add_trace(go.Scatter3d(
                x=result.raw_points[:, 0],
                y=result.raw_points[:, 1],
                z=result.raw_points[:, 2],
                mode="markers",
                marker=dict(size=1, color="red", opacity=0.1),
                name="Original chaos"))
            fig.add_trace(go.Scatter3d(
                x=result.clean_points[:, 0],
                y=result.clean_points[:, 1],
                z=result.clean_points[:, 2],
                mode="markers",
                marker=dict(size=3, color="gold", opacity=0.8),
                name="Filtered signal"))
            fig.update_layout(**scene)
            chart(fig)

        with tc:
            fig = go.Figure(go.Mesh3d(
                x=verts[:, 0],
                y=verts[:, 1],
                z=verts[:, 2],
                i=tris[:, 0],
                j=tris[:, 1],
                k=tris[:, 2],
                intensity=result.densities,
                colorscale="Viridis",
                colorbar=dict(title="Data support"),
                lighting=dict(ambient=0.5,
                              diffuse=0.5,
                              roughness=0.1,
                              specular=0.2)))
            fig.update_layout(**scene)
            chart(fig)
            st.caption("Yellow marks surface anchored by many real points; purple "
                       "marks regions interpolated by the Poisson equation. This "
                       "measures **reconstruction support**, not detection "
                       "certainty — for that, use bootstrap stability.")

        st.divider()
        st.subheader("💾 Export")
        e1, e2 = st.columns(2)
        with e1:
            st.download_button("📥 Mesh (.ply — preserves colours)",
                               core.export_mesh(result.mesh, ".ply"),
                               "chronos_artifact.ply",
                               "application/octet-stream")
        with e2:
            st.download_button("📥 Mesh (.obj — CAD / 3D printing)",
                               core.export_mesh(result.mesh, ".obj"),
                               "chronos_artifact.obj",
                               "application/octet-stream")