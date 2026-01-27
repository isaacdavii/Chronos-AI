# Se necessário usar o ambiente virtual, rode:
# source .venv/bin/activate  (Linux/Mac)
# .\venv\Scripts\activate (Windows)
# Depois, instale as dependências:
# pip install streamlit pandas scikit-learn plotly
# Rodar o app:
# streamlit run App/app_pt.py

# Desative o ambiente virtual após o uso:
# deactivate  (Linux/Mac/Windows)

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title = "Chronos: IA para Arqueologia",
    layout = "wide",
    page_icon = "🏛️"
)

# --- CABEÇALHO ---
st.title("🏛️ Chronos - Sistema de Detecção Arqueológica")
st.markdown("""
**Transforme dados brutos de radar em descobertas históricas.**
Este sistema utiliza o algoritmo *DBSCAN* para separar ruído geológico de estruturas arquitetônicas soterradas.
""")
st.markdown("---")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("1. Configuração de Dados")
uploaded_file = st.sidebar.file_uploader("Upload Arquivo GPR (CSV)", type = ["csv"])

st.sidebar.header("2. Calibragem da IA (DBSCAN)")
eps = st.sidebar.slider("Raio de Busca (Epsilon)", 0.5, 10.0, 3.0, help = "Distância máxima entre dois pontos para serem considerados vizinhos.")
min_samples = st.sidebar.slider("Densidade Mínima", 2, 20, 5, help = "Mínimo de pontos para formar um cluster inicial.")

st.sidebar.header("3. Refinamento (Pós-Processamento)")
min_cluster_size = st.sidebar.slider("Ignorar Clusters Pequenos (< Pontos)", 0, 100, 10, help = "Remove detritos pequenos detectados como estrutura.")

# --- FUNÇÃO DE DADOS DEMO ---
def gerar_dados_demo():
    # Geração procedural de uma "Muralha Curva e Ruído" (dados sintéticos para demonstração)
    np.random.seed(42) # Semente para reprodutibilidade
    N_RUIDO = 1500
    N_MURO = 500
    
    # Ruído disperso
    x_ruido = np.random.uniform(0, 100, N_RUIDO)
    y_ruido = np.random.uniform(0, 100, N_RUIDO)
    z_ruido = np.random.uniform(-10, 0, N_RUIDO)
    
    # Estrutura (Senoide com espessura)
    x_muro = np.linspace(10, 90, N_MURO)
    y_muro = 30 + 0.4 * x_muro + 15 * np.sin(x_muro / 10) + np.random.normal(0, 1.0, N_MURO)
    z_muro = np.random.normal(-3.0, 0.5, N_MURO) # Muro está a 3m de profundidade
    
    df_ruido = pd.DataFrame({'x': x_ruido, 'y': y_ruido, 'z': z_ruido, 'tipo': 'Ruído'})
    df_muro = pd.DataFrame({'x': x_muro, 'y': y_muro, 'z': z_muro, 'tipo': 'Muro Real'})
    
    return pd.concat([df_ruido, df_muro], ignore_index = True)

# --- CARREGAMENTO ---
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    # Mostra um aviso apenas se for a primeira carga
    st.sidebar.info("💡 Dica: Usando dados sintéticos de demonstração.")
    df = gerar_dados_demo()

# --- PROCESSAMENTO PRINCIPAL ---
# Botão de ação principal
if st.sidebar.button("🔍 Iniciar Escaneamento", type = "primary"):
    
    with st.spinner('Processando nuvem de pontos...'):
        # 1. Aplica DBSCAN
        modelo = DBSCAN(eps = eps, min_samples = min_samples)
        clusters = modelo.fit_predict(df[['x', 'y', 'z']])
        df['cluster'] = clusters

        # 2. Filtro Heurístico (Nova Lógica!)
        # Conta quantos pontos tem em cada cluster
        contagem = df['cluster'].value_counts()
        
        # Cria uma lista de clusters válidos (que são maiores que o filtro do slider)
        # O cluster -1 (ruído) é mantido separado
        clusters_validos = contagem[contagem > min_cluster_size].index.tolist()
        
        # Se o cluster for pequeno demais, vira ruído (-1)
        df['cluster_filtrado'] = df['cluster'].apply(lambda x: x if x in clusters_validos else -1)

        # 3. Estatísticas
        n_ruido = len(df[df['cluster_filtrado'] == -1])
        n_estrutura = len(df[df['cluster_filtrado'] != -1])
        n_clusters = df['cluster_filtrado'].nunique() - 1 # Remove o -1 da conta

        # Exibe Métricas no Topo
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Pontos Analisados", len(df))
        kpi2.metric("Ruído Descartado", f"{n_ruido} pts", delta = "-Rejeitados", delta_color = "inverse")
        kpi3.metric("Estrutura Confirmada", f"{n_estrutura} pts", delta = f"{n_clusters} Clusters", delta_color = "normal")

        # --- VISUALIZAÇÃO ---
        
        # Prepara legenda bonita
        df['Legenda'] = df['cluster_filtrado'].apply(lambda x: 'Ruído de Solo' if x == -1 else f'Estrutura #{x}')
        
        # TABS para separar 3D e 2D
        tab1, tab2 = st.tabs(["🌍 Visão 3D Interativa", "🗺️ Planta Baixa (2D)"])
        
        with tab1:
            fig_3d = px.scatter_3d(
                df, x = 'x', y = 'y', z = 'z', 
                color = 'Legenda',
                color_discrete_map = {'Ruído de Solo': 'lightgray'},
                opacity = 0.7,
                height = 600,
                title = "Modelo Volumétrico do Terreno"
            )
            fig_3d.update_traces(marker = dict(size = 3)) # Pontos menores ficam mais elegantes
            st.plotly_chart(fig_3d, use_container_width = True)

        with tab2:
            # Filtra apenas o que é estrutura para o mapa 2D ficar limpo
            df_mapa = df[df['cluster_filtrado'] != -1]
            
            if not df_mapa.empty:
                fig_2d = px.scatter(
                    df_mapa, x = 'x', y = 'y',
                    color = 'Legenda',
                    height = 600,
                    title = "Projeção Superior (Planta de Escavação)"
                )
                fig_2d.update_yaxes(scaleanchor = "x", scaleratio = 1) # Mantém proporção 1:1 real
                st.plotly_chart(fig_2d, use_container_width = True)
            else:
                st.warning("Nenhuma estrutura encontrada com esses parâmetros. Tente aumentar o Epsilon ou diminuir a Densidade.")

        # --- DOWNLOAD ---
        st.markdown("### 📥 Exportar Dados")
        csv = df[df['cluster_filtrado'] != -1].to_csv(index = False).encode('utf-8')
        st.download_button(
            label = "Baixar Relatório Vetorial (CSV)",
            data = csv,
            file_name = "chronos_detectado.csv",
            mime = "text/csv"
        )

else:

    st.info("👈 Ajuste os parâmetros na barra lateral e clique em 'Iniciar Escaneamento'.")
