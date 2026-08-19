"""
Chronos — processing core.

Language- and UI-agnostic. All pipeline logic lives here; the Streamlit apps
only translate strings and draw. Errors and warnings are returned as
language-neutral codes for the UI layer to map.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

try:
    import open3d as o3d

    HAS_OPEN3D = True
    OPEN3D_ERROR = None
except Exception as exc:  # ImportError, but also libGL failures
    o3d = None
    HAS_OPEN3D = False
    OPEN3D_ERROR = str(exc)

REQUIRED_COLUMNS = ("x", "y", "z")


def set_seed(seed: int = 42) -> None:
    """Fix every source of randomness used across the project."""
    import random as _random

    _random.seed(seed)
    np.random.seed(seed)
    try:
        if HAS_OPEN3D:
            o3d.utility.random.seed(seed)
    except AttributeError:
        pass


# =========================================================================== #
# Module 1 — density-based prospecting
# =========================================================================== #
def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """Check the schema before a raw KeyError reaches the interface.

    Returns (is_valid, reason_code).
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, f"MISSING_COLUMNS:{','.join(missing)}"
    if df.empty:
        return False, "EMPTY_FILE"

    sub = df[list(REQUIRED_COLUMNS)]
    if not all(np.issubdtype(t, np.number) for t in sub.dtypes):
        return False, "NON_NUMERIC_COLUMNS"

    n_null = int(sub.isna().any(axis=1).sum())
    if n_null:
        return False, f"NULL_ROWS:{n_null}"
    return True, "OK"


@dataclass
class ProspectingResult:
    """Outcome of a density scan. Build a new one rather than mutating."""

    df: pd.DataFrame
    n_clusters: int
    n_noise: int
    n_structure: int
    eps: float
    min_samples: int
    min_cluster_size: int


def prospect(df: pd.DataFrame, eps: float, min_samples: int,
             min_cluster_size: int = 10,
             standardize: bool = False) -> ProspectingResult:
    """DBSCAN plus a heuristic cluster-size filter.

    standardize: z-scores x/y/z before clustering. Leave it False when all
    three axes carry the same physical unit; turn it on when one of them is a
    different quantity, such as radar intensity, since mixing units inside a
    Euclidean metric splits single structures at arbitrary boundaries.
    """
    from sklearn.cluster import DBSCAN

    df = df.copy()
    X = df[list(REQUIRED_COLUMNS)].to_numpy(dtype=float)
    if standardize:
        from sklearn.preprocessing import StandardScaler

        X = StandardScaler().fit_transform(X)

    df["cluster"] = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)

    # Drop the noise label before measuring size, so a large noise set is never
    # counted as a valid cluster.
    counts = df.loc[df["cluster"] != -1, "cluster"].value_counts()
    keep = set(counts[counts >= min_cluster_size].index)
    df["cluster_filtered"] = df["cluster"].where(df["cluster"].isin(keep), -1)

    n_clusters = len(set(df["cluster_filtered"].unique()) - {-1})

    return ProspectingResult(
        df=df,
        n_clusters=n_clusters,
        n_noise=int((df["cluster_filtered"] == -1).sum()),
        n_structure=int((df["cluster_filtered"] != -1).sum()),
        eps=eps,
        min_samples=min_samples,
        min_cluster_size=min_cluster_size,
    )


def suggest_eps(df: pd.DataFrame, k: int = 8) -> float:
    """Knee of the k-distance plot, as a data-driven starting value for `eps`.

    Heuristic from Ester et al. (1996); knee detection in the spirit of Kneedle
    (Satopaa et al., 2011): the point furthest from the chord joining the two
    ends of the sorted k-distance curve.
    """
    from sklearn.neighbors import NearestNeighbors

    X = df[list(REQUIRED_COLUMNS)].to_numpy(dtype=float)
    k = min(k, len(X) - 1)
    d, _ = NearestNeighbors(n_neighbors=k + 1).fit(X).kneighbors(X)

    dk = np.sort(d[:, k])
    n = len(dk)
    p0, p1 = np.array([0.0, dk[0]]), np.array([n - 1.0, dk[-1]])
    v = (p1 - p0) / np.linalg.norm(p1 - p0)
    pts = np.column_stack([np.arange(n, dtype=float), dk]) - p0
    return float(dk[int(np.abs(pts[:, 0] * v[1] - pts[:, 1] * v[0]).argmax())])


def generalize_coordinates(df: pd.DataFrame, grid_m: float = 1000.0,
                           columns: tuple = ("x", "y"),
                           seed: int | None = 42) -> pd.DataFrame:
    """Snap coordinates to a coarse grid before publication.

    Publishing precise site coordinates enables looting; generalisation to a
    grid is the standard mitigation for sensitive heritage data. The z column
    is left untouched, since depth alone does not locate a site.

    Deliberately lossy and not reversible. Keep the ungeneralised file out of
    version control.
    """
    out = df.copy()
    rng = np.random.default_rng(seed)

    for col in columns:
        if col not in out.columns:
            continue
        # Sub-cell jitter keeps the lattice itself from becoming invertible.
        snapped = np.floor(out[col] / grid_m) * grid_m + grid_m / 2.0
        out[col] = snapped + rng.uniform(-grid_m / 4, grid_m / 4, len(out))

    out.attrs["generalized_grid_m"] = grid_m
    return out


# =========================================================================== #
# Module 2 — volumetric reconstruction
# =========================================================================== #
def _amphora_radius(z: float) -> float:
    """Profile of the synthetic amphora as a function of height."""
    if z < 1.0:
        return 2.0 + z * 0.5
    if z < 6.0:
        return 2.5 + 1.5 * np.sin((z - 1) * 0.8)
    if z < 8.0:
        return 1.5 + 0.5 * np.cos((z - 6) * 1.5)
    return 2.0 + (z - 8) * 0.5


def generate_amphora(seed: int = 42, layers: int = 150, per_layer: int = 100,
                     dropout: float = 0.3, n_noise: int = 8000,
                     jitter: float = 0.15) -> np.ndarray:
    """Synthetic amphora surface with sensor dropout, buried in volumetric noise.

    Sampling density matters more than it looks: below roughly 100 points per
    layer the shell becomes sparser than the surrounding noise and no
    local-density filter can separate the two.
    """
    rng = np.random.default_rng(seed)
    artifact = []

    for i in range(layers):
        z = (i / layers) * 10.0
        if rng.random() > dropout:
            theta = np.arange(per_layer) / per_layer * 2 * np.pi
            r = _amphora_radius(z) + rng.normal(0, jitter, per_layer)
            artifact.append(np.column_stack([r * np.cos(theta),
                                             r * np.sin(theta),
                                             np.full(per_layer, z)]))

    artifact = np.vstack(artifact)
    noise = np.column_stack([rng.uniform(-5, 5, n_noise),
                             rng.uniform(-5, 5, n_noise),
                             rng.uniform(-2, 12, n_noise)])

    every = np.vstack([artifact, noise])
    rng.shuffle(every)
    return every


def amphora_surface(layers: int = 400, per_layer: int = 200) -> np.ndarray:
    """Noise-free analytic surface, used as the reference for mesh metrics."""
    pts = []
    for i in range(layers):
        z = (i / layers) * 10.0
        r = _amphora_radius(z)
        theta = np.arange(per_layer) / per_layer * 2 * np.pi
        pts.append(np.column_stack([r * np.cos(theta), r * np.sin(theta),
                                    np.full(per_layer, z)]))
    return np.vstack(pts)


def load_las(file, voxel: float | None = None) -> tuple[np.ndarray, dict]:
    """Read .las/.laz, centre the cloud and voxel-downsample adaptively.

    The centring offset is returned in the metadata so it can be added back on
    export. Uncentred UTM coordinates degrade the precision of the Poisson
    octree, and a fixed voxel size is meaningless across scenes of different
    extents.
    """
    import laspy

    las = laspy.read(file)
    points = np.vstack((las.x, las.y, las.z)).transpose()
    n_raw = len(points)

    offset = points.mean(axis=0)
    points = points - offset

    extent = float(np.ptp(points, axis=0).max())
    if voxel is None:
        voxel = max(extent / 1500.0, 1e-4)

    if HAS_OPEN3D:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        points = np.asarray(pcd.voxel_down_sample(voxel_size=voxel).points)

    try:
        crs = las.header.parse_crs()
    except Exception:
        crs = None

    return points, {
        "n_raw": n_raw,
        "n_final": len(points),
        "voxel": voxel,
        "offset": offset,
        "extent": extent,
        "crs": str(crs) if crs else None,
    }


def _median_spacing(pcd) -> float:
    d = np.asarray(pcd.compute_nearest_neighbor_distance())
    d = d[np.isfinite(d) & (d > 0)]
    return float(np.median(d)) if len(d) else 1.0


@dataclass
class ReconstructionResult:
    raw_points: np.ndarray
    clean_points: np.ndarray
    mesh: object
    densities: np.ndarray
    metrology: dict = field(default_factory=dict)
    quality: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def reconstruct(points: np.ndarray, nb_neighbors: int = 50,
                std_ratio: float = 1.0, use_ransac: bool = False,
                ransac_dist: float = 0.5, use_dbscan: bool = True,
                poisson_depth: int = 8,
                prune_quantile: float = 0.05) -> ReconstructionResult:
    """Pipeline: SOR -> optional RANSAC -> DBSCAN -> Poisson -> metrology.

    The DBSCAN stage is what separates signal from background. SOR is a
    density-uniformity filter: it removes speckle but treats a uniform noise
    field as perfectly ordinary, so without a detector Poisson reconstructs the
    envelope of the noise cloud instead of the artifact.
    """
    if not HAS_OPEN3D:
        raise RuntimeError(f"Open3D unavailable: {OPEN3D_ERROR}")

    warnings: list[str] = []
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=float))

    # 1. Statistical outlier removal
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors,
                                            std_ratio=std_ratio)

    # 2. Optional ground removal
    if use_ransac and len(pcd.points) > 3:
        _, inliers = pcd.segment_plane(distance_threshold=ransac_dist,
                                       ransac_n=3, num_iterations=1000)
        if len(inliers) < len(pcd.points):
            pcd = pcd.select_by_index(inliers, invert=True)
        else:
            warnings.append("RANSAC_ALL_GROUND")

    # 3. Density detection
    if use_dbscan and len(pcd.points) > 10:
        spacing = _median_spacing(pcd)
        labels = np.asarray(pcd.cluster_dbscan(eps=3 * spacing, min_points=8,
                                               print_progress=False))
        if labels.max() >= 0:
            largest = np.bincount(labels[labels >= 0]).argmax()
            kept = np.where(labels == largest)[0]
            if len(kept) / len(labels) < 0.005:
                warnings.append("DBSCAN_CLUSTER_TINY")
            else:
                pcd = pcd.select_by_index(kept)
        else:
            warnings.append("DBSCAN_NO_CLUSTER")

    clean_points = np.asarray(pcd.points)
    if len(clean_points) < 50:
        raise ValueError(f"TOO_FEW_POINTS:{len(clean_points)}")

    # 4. Normals, with a radius derived from the cloud's own spacing
    spacing = _median_spacing(pcd)
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=4 * spacing,
                                                          max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(k=20)

    # Consistent orientation is not necessarily outward orientation, and an
    # inverted field yields an inside-out surface with negative volume.
    radial = clean_points - clean_points.mean(axis=0)
    normals = np.asarray(pcd.normals)
    if float(np.sum(np.einsum("ij,ij->i", radial, normals))) < 0:
        pcd.normals = o3d.utility.Vector3dVector(-normals)
        warnings.append("NORMALS_FLIPPED")

    # 5. Poisson reconstruction and density pruning
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=poisson_depth, width=0, scale=1.1, linear_fit=False)
    densities = np.asarray(densities)
    if len(mesh.vertices) == 0:
        raise ValueError("EMPTY_MESH")

    remove = densities < np.quantile(densities, prune_quantile)
    mesh.remove_vertices_by_mask(remove)
    # densities carries one value per vertex, so it has to be pruned alongside
    # the mesh or every vertex ends up coloured with another vertex's value.
    densities = densities[~remove]
    assert len(densities) == len(mesh.vertices), "densities misaligned"

    # 6. Topological cleanup
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_unreferenced_vertices()
    if len(densities) > len(mesh.vertices):
        densities = densities[: len(mesh.vertices)]

    # 7. Topology is checked, not assumed
    quality = {
        "watertight": bool(mesh.is_watertight()),
        "edge_manifold": bool(mesh.is_edge_manifold()),
        "vertex_manifold": bool(mesh.is_vertex_manifold()),
        "self_intersecting": bool(mesh.is_self_intersecting()),
        "orientable": bool(mesh.is_orientable()),
        "n_vertices": len(mesh.vertices),
        "n_triangles": len(mesh.triangles),
    }
    if not quality["watertight"]:
        warnings.append("MESH_NOT_WATERTIGHT")

    # 8. Metrology on the mesh. Four distinct quantities, reported separately:
    # collapsing them into one number is how an envelope gets mistaken for a
    # volume. True volume is only defined for a closed mesh.
    extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())
    metrology = {
        "width": float(extent[0]),
        "depth": float(extent[1]),
        "height": float(extent[2]),
        "volume_aabb": float(np.prod(extent)),
        "volume_obb": None,
        "volume_hull": None,
        "volume_true": None,
        "convexity": None,
    }

    try:
        metrology["volume_obb"] = float(mesh.get_oriented_bounding_box().volume())
    except Exception:
        pass

    try:
        hull, _ = mesh.compute_convex_hull()
        metrology["volume_hull"] = float(hull.get_volume())
    except Exception:
        pass

    if quality["watertight"]:
        try:
            metrology["volume_true"] = float(mesh.get_volume())
            if metrology["volume_hull"]:
                metrology["convexity"] = (metrology["volume_true"]
                                          / metrology["volume_hull"])
        except Exception:
            pass

    return ReconstructionResult(
        raw_points=np.asarray(points),
        clean_points=clean_points,
        mesh=mesh,
        densities=densities,
        metrology=metrology,
        quality=quality,
        warnings=warnings,
    )


# Bulk density in kg/m^3. GPR measures dielectric contrast, not composition, so
# the material is always the operator's hypothesis and needs XRF or direct
# analysis to confirm.
MATERIAL_DENSITY = {
    "loose_soil": 1_400,
    "compacted_soil": 1_800,
    "ceramic": 2_000,
    "limestone": 2_600,
    "granite": 2_700,
    "bronze": 8_800,
}


def mass_scenarios(volume: float, materials: dict | None = None) -> pd.DataFrame:
    """Mass under each material hypothesis.

    The volume is an upper bound on occupied space, not a quantity of matter.
    """
    materials = materials or MATERIAL_DENSITY
    return pd.DataFrame(
        [{"material": m, "density_kg_m3": rho, "mass_t": volume * rho / 1000.0}
         for m, rho in materials.items()]
    ).sort_values("mass_t").reset_index(drop=True)


def export_mesh(mesh, suffix: str = ".ply") -> bytes:
    """Serialize the mesh to bytes.

    Prefer .ply or .glb: .obj carries no vertex colour, so the confidence map
    does not survive an .obj export.
    """
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        name = tmp.name
    try:
        o3d.io.write_triangle_mesh(name, mesh)
        with open(name, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(name):
            os.unlink(name)