# Para essa nova fase precisamos usar Python 3.11 (Open3D não é compatível com 3.13 ainda). Então, crie um ambiente virtual específico para essa versão:
# Rode:
# Para Windows:
# py -3.11 -m venv .venv311
# .\.venv311\Scripts\activate  (Windows)
# Para Linux/Mac:
# python3.11 -m venv .venv311
# source .venv311/bin/activate  (Linux/Mac)

# Depois, instale as dependências:
# pip install -r requirements.txt

# Rodar o app:
# streamlit run App/app_pt.py

# Desative o ambiente virtual após o uso:
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

# =======================
# CONFIGURAÇÃO DA PÁGINA
# =======================
st.set_page_config(
    page_title = "Chronos: IA para Arqueologia", 
    layout = "wide", 
    page_icon = "🏛️"
)


# ==========
# CABEÇALHO
# ==========
st.title("🏛️ Chronos - Plataforma de Arqueologia Computacional")
st.markdown(
    "Sistema avançado para processamento de nuvens de pontos, detecção de anomalias (GPR) e reconstrução volumétrica de artefatos."
)
st.markdown("---")


# ==================================
# BARRA LATERAL: SELETOR DE MÓDULOS
# ==================================
st.sidebar.title("Navegação")
modulo = st.sidebar.radio(
    "Escolha o Módulo Analítico:",
    ["1️⃣ Prospecção de Terreno (DBSCAN)", "2️⃣ Reconstrução de Artefatos (Open3D)"],
)
st.sidebar.markdown("---")

# =========================================
# MÓDULO 1: O SEU CÓDIGO ORIGINAL (DBSCAN)
# =========================================
if modulo == "1️⃣ Prospecção de Terreno (DBSCAN)":
    st.header("Módulo 1: Detecção de Estruturas em Larga Escala")

    st.sidebar.header("1. Configuração de Dados")
    uploaded_file = st.sidebar.file_uploader("Upload Arquivo GPR (CSV)", type = ["csv"])

    st.sidebar.header("2. Calibragem da IA (DBSCAN)")
    eps = st.sidebar.slider("Raio de Busca (Epsilon)", 0.5, 10.0, 3.0)
    min_samples = st.sidebar.slider("Densidade Mínima", 2, 20, 5)

    st.sidebar.header("3. Refinamento")
    min_cluster_size = st.sidebar.slider(
        "Ignorar Clusters Pequenos (< Pontos)", 0, 100, 10
    )

    def gerar_dados_demo_muro():
        np.random.seed(42)
        N_RUIDO, N_MURO = 1500, 500
        x_ruido = np.random.uniform(0, 100, N_RUIDO)
        y_ruido = np.random.uniform(0, 100, N_RUIDO)
        z_ruido = np.random.uniform(-10, 0, N_RUIDO)
        x_muro = np.linspace(10, 90, N_MURO)
        y_muro = (
            30
            + 0.4 * x_muro
            + 15 * np.sin(x_muro / 10)
            + np.random.normal(0, 1.0, N_MURO)
        )
        z_muro = np.random.normal(-3.0, 0.5, N_MURO)
        df_ruido = pd.DataFrame(
            {"x": x_ruido, "y": y_ruido, "z": z_ruido, "tipo": "Ruído"}
        )
        df_muro = pd.DataFrame(
            {"x": x_muro, "y": y_muro, "z": z_muro, "tipo": "Muro Real"}
        )
        return pd.concat([df_ruido, df_muro], ignore_index = True)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        st.info("💡 Exibindo dados sintéticos de demonstração (Muralha Oculta).")
        df = gerar_dados_demo_muro()

    if st.sidebar.button("🔍 Iniciar Escaneamento", type = "primary"):
        with st.spinner("Processando nuvem de pontos com DBSCAN..."):
            modelo = DBSCAN(eps = eps, min_samples = min_samples)
            df["cluster"] = modelo.fit_predict(df[["x", "y", "z"]])

            contagem = df["cluster"].value_counts()
            clusters_validos = contagem[contagem > min_cluster_size].index.tolist()
            df["cluster_filtrado"] = df["cluster"].apply(
                lambda x: x if x in clusters_validos else -1
            )

            n_ruido = len(df[df["cluster_filtrado"] == -1])
            n_estrutura = len(df[df["cluster_filtrado"] != -1])
            n_clusters = df["cluster_filtrado"].nunique() - 1

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Pontos Analisados", len(df))
            kpi2.metric("Ruído Descartado", f"{n_ruido} pts")
            kpi3.metric(
                "Estrutura Confirmada",
                f"{n_estrutura} pts",
                delta = f"{n_clusters} Clusters",
            )

            df["Legenda"] = df["cluster_filtrado"].apply(
                lambda x: "Ruído de Solo" if x == -1 else f"Estrutura #{x}"
            )

            tab1, tab2 = st.tabs(["🌍 Visão 3D Interativa", "🗺️ Planta Baixa (2D)"])
            with tab1:
                fig_3d = px.scatter_3d(
                    df,
                    x = "x",
                    y = "y",
                    z = "z",
                    color = "Legenda",
                    color_discrete_map = {"Ruído de Solo": "lightgray"},
                    height = 600,
                )
                fig_3d.update_traces(marker = dict(size = 3))
                st.plotly_chart(fig_3d, use_container_width = True)
            with tab2:
                df_mapa = df[df["cluster_filtrado"] != -1]
                if not df_mapa.empty:
                    fig_2d = px.scatter(
                        df_mapa, 
                        x = "x", 
                        y = "y", 
                        color = "Legenda", 
                        height = 600
                    )
                    fig_2d.update_yaxes(scaleanchor = "x", scaleratio = 1)
                    st.plotly_chart(fig_2d, use_container_width = True)
                    
            st.markdown("---")
            st.subheader("💾 Exportação de Dados")
            
            # Converte o DataFrame limpo (sem ruído) para CSV
            csv = df_mapa.to_csv(index = False).encode('utf-8')
            
            st.download_button(
                label = "📥 Baixar Planta Vetorial (.csv)",
                data = csv,
                file_name = "planta_arqueologica_chronos.csv",
                mime = "text/csv"
            )

# ===========================================
# MÓDULO 2: O CÓDIGO NOVO (OPEN3D / POISSON)
# ===========================================
elif modulo == "2️⃣ Reconstrução de Artefatos (Open3D)":
    if o3d is None:
        st.error(
            "⚠️ A biblioteca Open3D não está instalada ou não é compatível com sua versão do Python (3.13). Por favor, use Python 3.10 ou 3.11 para acessar este módulo."
        )
        st.stop()

    st.header("Módulo 2: Micro-Escavação e Reconstrução 3D")

    st.sidebar.header("1. Entrada de Dados")
    fonte_dados = st.sidebar.selectbox(
        "Fonte de Dados:",
        ["Simulação: Ânfora com Ruído", "Upload Arquivo LIDAR (.las)"],
    )
    arquivo_las = None
    if fonte_dados == "Upload Arquivo LIDAR (.las)":
        arquivo_las = st.sidebar.file_uploader(
            "Upload LIDAR (.las / .laz)", type = ["las", "laz"]
        )

    st.sidebar.header("2. Limpeza Digital")
    nb_neighbors = st.sidebar.slider(
        "Filtro: Vizinhos",
        10,
        100,
        50,
        help = "Quantos vizinhos um ponto precisa para não ser considerado poeira.",
    )
    std_ratio = st.sidebar.slider(
        "Filtro: Rigor", 0.1, 3.0, 1.0, help = "Menor = Mais rigoroso na limpeza."
    )
    st.sidebar.markdown("---")
    usar_ransac = st.sidebar.checkbox("Ativar Remoção de Solo (RANSAC)", value = False, help = "Remove o terreno para isolar as ruínas.")
    ransac_dist = st.sidebar.slider("Tolerância do Solo (m)", 0.1, 2.0, 0.5, help = "Aumente se o chão for muito irregular (colinas).")

    st.sidebar.header("3. Meshing (Superfície)")
    poisson_depth = st.sidebar.slider(
        "Resolução da Malha",
        6,
        10,
        8,
        help = "Maior = Mais detalhes, mas exige mais processamento.",
    )

    # Função para gerar a ânfora sintética
    @st.cache_data
    def gerar_anfora_suja():
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

    # Prepara os pontos baseados na escolha do usuário
    pontos_brutos = None
    if fonte_dados == "Simulação: Ânfora com Ruído":
        st.info(
            "💡 Usando varredura sintética de um artefato cerâmico (Ânfora) altamente ruidoso."
        )
        pontos_brutos = gerar_anfora_suja()
    elif arquivo_las is not None:
        with st.spinner("Lendo arquivo LIDAR e aplicando Voxel Downsampling..."):
            las = laspy.read(arquivo_las)
            pontos_reais = np.vstack((las.x, las.y, las.z)).transpose()
            # Voxel Downsampling automático para evitar travamento na nuvem
            pcd_temp = o3d.geometry.PointCloud()
            pcd_temp.points = o3d.utility.Vector3dVector(pontos_reais)
            pcd_down = pcd_temp.voxel_down_sample(voxel_size = 0.05)  # 5cm Voxel
            pontos_brutos = np.asarray(pcd_down.points)
            st.success(
                f"LIDAR carregado e otimizado! (De {len(pontos_reais)} para {len(pontos_brutos)} pontos)."
            )

    if (
        st.sidebar.button("⚙️ Iniciar Reconstrução", type = "primary")
        and pontos_brutos is not None
    ):

        # 1. Filtro Estatístico
        with st.spinner(
            "Passo 1: Removendo areia e detritos (Statistical Outlier Removal)..."
        ):
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(pontos_brutos)
            pcd_clean, ind = pcd.remove_statistical_outlier(
                nb_neighbors = nb_neighbors, std_ratio = std_ratio
            )
            pcd_clean = pcd.select_by_index(ind)
            
            if usar_ransac:
                with st.spinner("Passo 1.5: Dinamitando o solo topográfico (RANSAC)..."):
                    # segment_plane acha o chão. 'invert = True' guarda tudo que NÃO é o chão.
                    plane_model, inliers = pcd_clean.segment_plane(distance_threshold = ransac_dist,
                                                                   ransac_n = 3,
                                                                   num_iterations = 1000)
                    pcd_clean = pcd_clean.select_by_index(inliers, invert = True)
            
            pontos_limpos = np.asarray(pcd_clean.points)

        # 2. Reconstrução Poisson
        with st.spinner(
            "Passo 2: Calculando normais e tecendo malha sólida (Poisson Reconstruction)..."
        ):
            pcd_clean.estimate_normals(
                search_param = o3d.geometry.KDTreeSearchParamHybrid(radius = 1.0, max_nn = 30)
            )
            pcd_clean.orient_normals_consistent_tangent_plane(k = 20)
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                pcd_clean, depth = poisson_depth
            )

            # Corta excessos do Poisson
            densities = np.asarray(densities)
            vertices_to_remove = densities < np.quantile(densities, 0.05)
            mesh.remove_vertices_by_mask(vertices_to_remove)

            verts = np.asarray(mesh.vertices)
            tris = np.asarray(mesh.triangles)

        # 3. Metrologia
        with st.spinner("Passo 3: Calculando dimensões da descoberta..."):
            bbox = pcd_clean.get_axis_aligned_bounding_box()
            min_b, max_b = bbox.get_min_bound(), bbox.get_max_bound()
            dim_x, dim_y, dim_z = (
                max_b[0] - min_b[0],
                max_b[1] - min_b[1],
                max_b[2] - min_b[2],
            )
            volume_box = dim_x * dim_y * dim_z

        # EXIBIÇÃO DE RESULTADOS
        st.subheader("Resultados da Escavação Digital")

        # KPIs Metrológicos
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Largura (X)", f"{dim_x:.2f} m")
        col2.metric("Profundidade (Y)", f"{dim_y:.2f} m")
        col3.metric("Altura (Z)", f"{dim_z:.2f} m")
        col4.metric("Volume de Ocupação", f"{volume_box:.2f} m³")

        tabA, tabB = st.tabs(
            ["✨ Artefato Reconstruído (Malha 3D)", "🧹 Nuvem de Pontos Limpa"]
        )

        with tabA:
            # Gráfico do Objeto Sólido Dourado
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
                        name = "Artefato",
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
            # Gráfico comparativo Antes/Depois
            fig_pts = go.Figure()
            # Ruído original (em vermelho opaco e pequeno)
            fig_pts.add_trace(
                go.Scatter3d(
                    x = pontos_brutos[:, 0],
                    y = pontos_brutos[:, 1],
                    z = pontos_brutos[:, 2],
                    mode = "markers",
                    marker = dict(size = 1, color = "red", opacity = 0.1),
                    name = "Caos Original",
                )
            )
            # Pontos Limpos (em ouro)
            fig_pts.add_trace(
                go.Scatter3d(
                    x = pontos_limpos[:, 0],
                    y = pontos_limpos[:, 1],
                    z = pontos_limpos[:, 2],
                    mode = "markers",
                    marker = dict(size = 3, color = "gold", opacity = 0.8),
                    name = "Sinal Filtrado",
                )
            )
            fig_pts.update_layout(
                scene = dict(aspectmode = "data", bgcolor = "black"),
                paper_bgcolor = "black",
                height = 600,
                margin = dict(l = 0, r = 0, b = 0, t = 0),
            )
            st.plotly_chart(fig_pts, use_container_width = True)
        
        # Exportação de Dados
        st.markdown("---")
        st.subheader("💾 Exportação de Dados")

        with tempfile.NamedTemporaryFile(delete = False, suffix = ".obj") as tmp:
            tmp_name = tmp.name
        
        o3d.io.write_triangle_mesh(tmp_name, mesh)
        with open(tmp_name, "rb") as f:
            obj_data = f.read()
            
        os.unlink(tmp_name)  # Para limpar o arquivo temporário da memória do servidor

        st.download_button(
            label = "📥 Baixar Gêmeo Digital (.obj)",
            data = obj_data,
            file_name = "artefato_reconstruido_chronos.obj",
            mime = "application/octet-stream"
        )