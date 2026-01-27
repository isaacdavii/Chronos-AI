> 🇺🇸 **To read the English version of this project, [click here](README.md).**

---

# 🏛️ Chronos: Sistema de Detecção Arqueológica via IA

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Machine Learning](https://img.shields.io/badge/AI-Unsupervised-orange)
![Status](https://img.shields.io/badge/Status-Prototype-green)

> **"A tecnologia não reinventa o passado, mas nos dá novas lentes para enxergá-lo."**

## 📖 Sobre o Projeto

O **Chronos** é um sistema de Inteligência Artificial focado em **Arqueologia Computacional**. O projeto utiliza algoritmos de Machine Learning Não Supervisionado (**DBSCAN**) para identificar padrões estruturais (muralhas, fundações, necrópoles) ocultos em dados geofísicos ruidosos.

O objetivo é simular o processamento de dados reais de campo — como **GPR** (Radar de Penetração no Solo) e **LIDAR** — automatizando a detecção de sítios arqueológicos e gerando relatórios de escavação precisos.

---

## 🇻🇦 Motivação: O Desafio do Vaticano

Uma das grandes inspirações para o desenvolvimento do *Chronos* foi a complexidade arqueológica enfrentada por instituições como o Vaticano. A **Basílica de São Pedro** assenta-se sobre milênios de história estratificada, onde escavações físicas são arriscadas ou impossíveis.

O projeto busca responder: **Como mapear o sagrado sem tocá-lo?**
* **Arqueologia Não-Invasiva:** Processamento de sinais de radar para ver através do mármore.
* **Preservação:** Identificação de vazios e estruturas sem a necessidade de escavação destrutiva.

---

## 🛠️ Tecnologias e Inspirações

Este repositório serve como guia de estudos sobre tecnologias que estão revolucionando a história (inspirado pelo canal *Estranha História*, do Prof. Dr. Henrique Caldeira):

* **LIDAR (*Light Detection and Ranging*):** Modelagem 3D de terreno via laser para remover vegetação virtualmente.
* **XRF (*X-Ray Fluorescence*):** Análise química de materiais via raios-x.
* **DBSCAN (Algoritmo Principal):** Clusterização baseada em densidade espacial para separar "Sinal" (Muros) de "Ruído" (Pedras soltas).

---

## 📂 Estrutura do Repositório

O projeto está dividido em dois módulos progressivos:

### 1. [Chronos Parte I: Fundamentos Vetoriais](Chronos_Aqueologia_Parte_I.ipynb)
Focado na introdução à geometria computacional e detecção de padrões lineares.
* **Cenários:** Muralha Inca (Senoide) e Aldeia Circular.
* **Técnica:** Dados vetoriais ($X, Y, Z$).
* **Visualização:** Gráficos de dispersão e Mapas Folium.

### 2. [Chronos Parte II: Simulação Avançada (Raster)](Chronos_Arqueologia_Parte_II.ipynb)
Simulação de uma prospecção geofísica real (GPR) em alta resolução.
* **Cenário:** Uma "Basílica Subterrânea" oculta em uma matriz de 4 milhões de pontos.
* **Pipeline:**
    1.  **Ingestão Raster:** Tratamento de imagem e histogramas de sinal.
    2.  **Vetorização:** Conversão de Heatmap para Vetores.
    3.  **Classe `ChronosAnalyzer`:** Arquitetura orientada a objetos para processamento.
    4.  **Business Intelligence:** Geração automática de relatórios com áreas ($m^2$) e coordenadas de escavação.

---

## 📊 Resultados Visuais

O sistema é capaz de transformar dados brutos e ruidosos em plantas baixas limpas:

| Dados Brutos (Simulação GPR) | Detecção por IA (DBSCAN) | Planta Final (Vetorizada) |
|:---:|:---:|:---:|
| *Ruído e Sinal Misturados* | *Clusterização 3D* | *Estruturas Identificadas* |
| (Inserir imagem do Heatmap) | (Inserir imagem do Plotly) | (Inserir imagem da Planta) |

> *Exemplo: O sistema filtrou 95% do ruído geológico e identificou a planta em Cruz Latina da basílica simulada.*

---

## 🚀 Como Executar

Este projeto foi desenvolvido para rodar no **Google Colab** ou **Jupyter Notebook**.

### Pré-requisitos
```bash
pip install pandas numpy scikit-learn plotly folium matplotlib
```

---

## 👨‍💻 Autor

**Isaac Davi** *Desenvolvedor*

Construído como um projeto de portfólio explorando a interseção entre **História** e **Tecnologia**.  
Sinta-se à vontade para entrar em contato para colaborações ou dúvidas.

---

## 📄 Licença

Este projeto é de uso **acadêmico e educacional**.

* **Livre uso:** Você pode modificar e distribuir este código para fins de aprendizado e pesquisa.
* **Dados Sintéticos:** Observe que os dados arqueológicos gerados neste pipeline são **simulados** (geração procedural) e não representam sítios reais protegidos.

---
