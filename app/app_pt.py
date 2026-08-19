"""
Chronos — Plataforma de Arqueologia Computacional (interface em português).

Execução:
    pip install -r requirements.txt
    streamlit run app/app_pt.py

Toda a lógica vive em `chronos_core.py`, compartilhado com `app_en.py`. Este
arquivo apenas traduz e desenha.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import chronos_core as core

# O core devolve códigos neutros de idioma; a UI os transforma em frases.
AVISOS = {
    "RANSAC_ALL_GROUND": "O RANSAC classificou toda a nuvem como solo; a etapa "
                         "foi ignorada.",
    "DBSCAN_CLUSTER_TINY": "O maior cluster coerente é minúsculo; a detecção por "
                           "densidade foi ignorada.",
    "DBSCAN_NO_CLUSTER": "O DBSCAN não encontrou cluster coerente; a etapa foi "
                         "ignorada.",
    "NORMALS_FLIPPED": "As normais apontavam para dentro; a orientação foi "
                       "corrigida automaticamente.",
    "MESH_NOT_WATERTIGHT": "A malha não é hermética — a poda por densidade abre "
                           "buracos por construção. O volume real fica "
                           "indefinido; use o envelope.",
}

ERROS = {
    "EMPTY_FILE": "O arquivo está vazio.",
    "NON_NUMERIC_COLUMNS": "As colunas x, y e z precisam ser numéricas.",
    "EMPTY_MESH": "O Poisson gerou uma malha vazia. Reduza a resolução.",
}


def descrever_erro(codigo: str) -> str:
    """Traduz um código de erro do core para uma frase legível."""
    cabeca, _, detalhe = codigo.partition(":")
    if cabeca == "MISSING_COLUMNS":
        return f"colunas ausentes: {detalhe}"
    if cabeca == "NULL_ROWS":
        return f"{detalhe} linhas contêm valores nulos"
    if cabeca == "TOO_FEW_POINTS":
        return (f"só restaram {detalhe} pontos após a filtragem. Afrouxe o rigor "
                "do filtro.")
    return ERROS.get(cabeca, codigo)


st.set_page_config(page_title="Chronos: IA para Arqueologia",
                   layout="wide",
                   page_icon="🏛️")


def grafico(fig, **kw):
    """`width='stretch'` é a API recente; `use_container_width` é a antiga."""
    try:
        st.plotly_chart(fig, width="stretch", **kw)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, **kw)


st.title("🏛️ Chronos — Plataforma de Arqueologia Computacional")
st.caption("Processamento de nuvens de pontos, detecção de anomalias e "
           "reconstrução volumétrica de artefatos.")
st.divider()

st.sidebar.title("Navegação")
modulo = st.sidebar.radio("Módulo analítico:",
                          ["1️⃣ Prospecção de Terreno (DBSCAN)",
                           "2️⃣ Reconstrução de Artefatos (Open3D)"])
st.sidebar.divider()

# =========================================================================== #
# MÓDULO 1
# =========================================================================== #
if modulo.startswith("1"):
    st.header("Módulo 1 — Detecção de estruturas em larga escala")

    st.sidebar.header("1. Dados")
    arquivo = st.sidebar.file_uploader("Arquivo GPR (CSV com x, y, z)",
                                       type=["csv"])

    @st.cache_data
    def demo_muro(seed: int = 42) -> pd.DataFrame:
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

    if arquivo is not None:
        try:
            df = pd.read_csv(arquivo)
        except Exception as exc:
            st.error(f"Não consegui ler o CSV: {exc}")
            st.stop()

        valido, motivo = core.validate_dataframe(df)
        if not valido:
            st.error(f"Arquivo inválido — {descrever_erro(motivo)}. O CSV precisa "
                     "das colunas numéricas `x`, `y` e `z`.")
            st.stop()
        st.success(f"{len(df):,} pontos carregados.")
    else:
        st.info("Exibindo dados sintéticos de demonstração (muralha oculta).")
        df = demo_muro()

    st.sidebar.header("2. Calibragem do DBSCAN")
    if st.sidebar.button("📐 Sugerir epsilon"):
        st.session_state["eps_hint"] = core.suggest_eps(df)

    default_eps = float(st.session_state.get("eps_hint", 3.0))
    if "eps_hint" in st.session_state:
        st.sidebar.caption(f"Joelho da k-distância: {default_eps:.2f}")

    with st.sidebar.form("form_prospecting"):
        eps = st.slider("Raio de busca (epsilon)", 0.5, 10.0,
                        min(max(default_eps, 0.5), 10.0), 0.1)
        min_samples = st.slider("Densidade mínima", 2, 20, 5)
        min_size = st.slider("Ignorar clusters com menos de N pontos",
                             0, 100, 10)
        run = st.form_submit_button("🔍 Iniciar escaneamento", type="primary")

    if run:
        with st.spinner("Processando nuvem de pontos…"):
            st.session_state["prospecting_result"] = core.prospect(
                df, eps, min_samples, min_size)

    # Ler do session_state mantém os resultados vivos entre reruns de widget.
    result = st.session_state.get("prospecting_result")
    if result is not None:
        d = result.df

        k1, k2, k3 = st.columns(3)
        k1.metric("Pontos analisados", f"{len(d):,}")
        k2.metric("Ruído descartado", f"{result.n_noise:,}")
        k3.metric("Estrutura confirmada", f"{result.n_structure:,}",
                  delta=f"{result.n_clusters} clusters")

        if result.n_clusters == 0:
            st.warning("Nenhum cluster passou nos filtros. Aumente o epsilon ou "
                       "reduza a densidade mínima.")
        else:
            d["Legenda"] = np.where(
                d["cluster_filtered"] == -1, "Ruído de solo",
                "Estrutura #" + d["cluster_filtered"].astype(str))

            t1, t2 = st.tabs(["🌍 Visão 3D", "🗺️ Planta baixa"])
            with t1:
                fig = px.scatter_3d(d,
                                    x="x",
                                    y="y",
                                    z="z",
                                    color="Legenda",
                                    color_discrete_map={"Ruído de solo": "lightgray"},
                                    height=600)
                fig.update_traces(marker=dict(size=3))
                grafico(fig)

            plan = d[d["cluster_filtered"] != -1]
            with t2:
                fig = px.scatter(plan,
                                 x="x",
                                 y="y",
                                 color="Legenda",
                                 height=600)
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                grafico(fig)

            st.divider()
            st.subheader("💾 Exportação")
            st.download_button("📥 Planta vetorial (.csv)",
                               plan.to_csv(index=False).encode("utf-8"),
                               "planta_arqueologica_chronos.csv",
                               "text/csv")
            st.caption("Coordenadas precisas de sítios facilitam saque. Considere "
                       "generalizar a localização antes de publicar. No Brasil, "
                       "sítios são bens da União (Lei 3.924/1961) e a prospecção "
                       "requer autorização do IPHAN.")

# =========================================================================== #
# MÓDULO 2
# =========================================================================== #
else:
    if not core.HAS_OPEN3D:
        st.error(f"Open3D indisponível neste ambiente.\n\n`{core.OPEN3D_ERROR}`\n\n"
                 "O Open3D 0.19 publica wheels apenas para Python 3.8–3.12. "
                 "Instale com `pip install open3d` num ambiente compatível.")
        st.stop()

    st.header("Módulo 2 — Micro-escavação e reconstrução 3D")

    st.sidebar.header("1. Entrada")
    source = st.sidebar.selectbox("Fonte de dados:",
                                  ["Simulação: ânfora com ruído",
                                   "Upload LIDAR (.las / .laz)"])
    las_file = None
    if source.startswith("Upload"):
        las_file = st.sidebar.file_uploader("LIDAR", type=["las", "laz"])

    with st.sidebar.form("form_reconstruction"):
        st.subheader("2. Limpeza")
        nb_neighbors = st.slider("Filtro: vizinhos", 10, 100, 50)
        std_ratio = st.slider("Filtro: rigor", 0.1, 3.0, 1.0, 0.1,
                              help="Menor é mais agressivo.")
        use_dbscan = st.checkbox(
            "Isolar maior estrutura coerente (DBSCAN)", value=True,
            help="Detecta o artefato antes de reconstruir. Sem isso o Poisson "
                 "modela o envelope do ruído, não o objeto.")
        use_ransac = st.checkbox("Remover solo (RANSAC)", value=False)
        ransac_dist = st.slider("Tolerância do solo", 0.1, 2.0, 0.5, 0.1)

        st.subheader("3. Malha")
        poisson_depth = st.slider("Resolução (Poisson depth)", 6, 10, 8)
        prune_quantile = st.slider("Poda por densidade (quantil)",
                                   0.0, 0.30, 0.05, 0.01)
        run = st.form_submit_button("⚙️ Iniciar reconstrução", type="primary")

    points = None
    if source.startswith("Simulação"):
        st.info("Varredura sintética de uma ânfora cerâmica com ruído volumétrico.")
        points = core.generate_amphora(seed=42)
    elif las_file is not None:
        with st.spinner("Lendo LIDAR…"):
            points, meta = core.load_las(las_file)
        st.success(f"{meta['n_raw']:,} → {meta['n_final']:,} pontos "
                   f"(voxel adaptativo de {meta['voxel']:.3f}).")
        if meta["crs"] is None:
            st.warning("O arquivo não declara sistema de referência (CRS). Sem "
                       "CRS a nuvem não pode ser combinada com outros dados.")

    if run and points is not None:
        try:
            with st.spinner("SOR → detecção → Poisson → metrologia…"):
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
            st.error(f"A reconstrução falhou: {descrever_erro(str(exc))}")
            st.session_state.pop("reconstruction_result", None)
        except Exception as exc:
            st.error(f"A reconstrução falhou: {exc}")
            st.session_state.pop("reconstruction_result", None)
    elif run:
        st.warning("Carregue um arquivo antes de reconstruir.")

    result = st.session_state.get("reconstruction_result")
    if result is not None:
        for code in result.warnings:
            st.warning(AVISOS.get(code, code))

        st.subheader("Resultados")
        met, quality = result.metrology, result.quality

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Largura (X)", f"{met['width']:.2f}")
        c2.metric("Profundidade (Y)", f"{met['depth']:.2f}")
        c3.metric("Altura (Z)", f"{met['height']:.2f}")
        c4.metric("Volume real",
                  f"{met['volume_true']:.2f}" if met["volume_true"] else "indefinido")
        st.caption("As unidades seguem o arquivo de entrada. Um `.las` "
                   "georreferenciado traz metros; a simulação é adimensional.")

        with st.expander("📐 Volumetria detalhada e qualidade da malha"):
            v1, v2 = st.columns(2)
            with v1:
                st.markdown("**Volumes** (do maior envelope ao volume real)")
                st.write({
                    "Envelope AABB": round(met["volume_aabb"], 3),
                    "Envelope orientado (OBB)":
                        round(met["volume_obb"], 3) if met["volume_obb"] else None,
                    "Fecho convexo":
                        round(met["volume_hull"], 3) if met["volume_hull"] else None,
                    "Volume real (malha)":
                        round(met["volume_true"], 3) if met["volume_true"]
                        else "requer malha hermética",
                    "Convexidade (real/hull)":
                        round(met["convexity"], 3) if met["convexity"] else None,
                })
            with v2:
                st.markdown("**Topologia**")
                st.write({
                    "Hermética (watertight)": quality["watertight"],
                    "Edge-manifold": quality["edge_manifold"],
                    "Vertex-manifold": quality["vertex_manifold"],
                    "Orientável": quality["orientable"],
                    "Sem auto-interseção": not quality["self_intersecting"],
                    "Vértices": quality["n_vertices"],
                    "Triângulos": quality["n_triangles"],
                })

        if met["volume_hull"]:
            with st.expander("⚖️ Massa sob cada hipótese de material"):
                st.dataframe(core.mass_scenarios(met["volume_hull"]).round(2),
                             hide_index=True)
                st.caption("O volume do fecho convexo é um limite superior do "
                           "espaço ocupado, não uma quantidade de matéria. O GPR "
                           "mede contraste dielétrico, não composição — o material "
                           "é hipótese do operador e exige XRF ou análise direta "
                           "para confirmar.")

        verts = np.asarray(result.mesh.vertices)
        tris = np.asarray(result.mesh.triangles)
        ta, tb, tc = st.tabs(["✨ Artefato reconstruído", "🧹 Nuvem filtrada",
                              "📊 Mapa de confiança"])

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
            grafico(fig)

        with tb:
            fig = go.Figure()
            fig.add_trace(go.Scatter3d(
                x=result.raw_points[:, 0],
                y=result.raw_points[:, 1],
                z=result.raw_points[:, 2],
                mode="markers",
                marker=dict(size=1, color="red", opacity=0.1),
                name="Caos original"))
            fig.add_trace(go.Scatter3d(
                x=result.clean_points[:, 0],
                y=result.clean_points[:, 1],
                z=result.clean_points[:, 2],
                mode="markers",
                marker=dict(size=3, color="gold", opacity=0.8),
                name="Sinal filtrado"))
            fig.update_layout(**scene)
            grafico(fig)

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
                colorbar=dict(title="Suporte de dado"),
                lighting=dict(ambient=0.5,
                              diffuse=0.5,
                              roughness=0.1,
                              specular=0.2)))
            fig.update_layout(**scene)
            grafico(fig)
            st.caption("Amarelo marca superfície ancorada em muitos pontos reais; "
                       "roxo marca regiões interpoladas pela equação de Poisson. "
                       "Isso mede **suporte de reconstrução**, não certeza de "
                       "detecção — para isso, use estabilidade por bootstrap.")

        st.divider()
        st.subheader("💾 Exportação")
        e1, e2 = st.columns(2)
        with e1:
            st.download_button("📥 Malha (.ply — preserva cores)",
                               core.export_mesh(result.mesh, ".ply"),
                               "artefato_chronos.ply",
                               "application/octet-stream")
        with e2:
            st.download_button("📥 Malha (.obj — CAD / impressão 3D)",
                               core.export_mesh(result.mesh, ".obj"),
                               "artefato_chronos.obj",
                               "application/octet-stream")