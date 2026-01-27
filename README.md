> 🇧🇷 **Para ler a versão em Português deste projeto, [clique aqui](README.pt-br.md).**

---

# 🏛️ Chronos: Archaeological AI Detection System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Machine Learning](https://img.shields.io/badge/AI-Unsupervised-orange)
![Status](https://img.shields.io/badge/Status-Prototype-green)

> **"Technology does not reinvent the past, but gives us new lenses to see it."**

## 📖 About the Project

**Chronos** is an Artificial Intelligence system focused on **Computational Archaeology**. The project utilizes Unsupervised Machine Learning algorithms (**DBSCAN**) to identify structural patterns (walls, foundations, necropolises) hidden within noisy geophysical data.

The goal is to simulate the processing of real field data — such as **GPR** (Ground Penetrating Radar) and **LIDAR** — automating the detection of archaeological sites and generating precise excavation reports.

---

## 🇻🇦 Motivation: The Vatican Challenge

One of the major inspirations for the development of *Chronos* was the archaeological complexity faced by institutions like the Vatican. **St. Peter's Basilica** sits upon millennia of stratified history, where physical excavations are risky or impossible.

The project seeks to answer: **How to map the sacred without touching it?**
* **Non-Invasive Archaeology:** Processing radar signals to see through marble.
* **Preservation:** Identification of voids and structures without the need for destructive excavation.

---

## 🛠️ Technologies and Inspirations

This repository serves as a study guide on technologies that are revolutionizing history (inspired by the channel [*Estranha História*](https://www.youtube.com/@henriquecaldeira), by Prof. Dr. Henrique Caldeira):

* **LIDAR (*Light Detection and Ranging*):** 3D terrain modeling via laser to virtually remove vegetation.
* **XRF (*X-Ray Fluorescence*):** Chemical analysis of materials via X-rays.
* **DBSCAN (Main Algorithm):** Spatial density-based clustering to separate "Signal" (Walls) from "Noise" (Loose stones).

---

## 📂 Repository Structure

The project is divided into two progressive modules:

### 1. [Chronos Part I: Vector Fundamentals](Notebooks/en/Chronos_Archaeology_Part_I.ipynb)
Focused on the introduction to computational geometry and linear pattern detection.
* **Scenarios:** Inca Wall (Sine wave), Circular Village, and Necropolis.
* **Technique:** Vector data ($X, Y, Z$).
* **Visualization:** Scatter plots and Folium Maps.

### 2. [Chronos Part II: Advanced Simulation (Raster)](Notebooks/en/Chronos_Aqueologia_Parte_II.ipynb)
Simulation of a real high-resolution geophysical survey (GPR).
* **Scenario:** A "Subterranean Basilica" hidden in a 4-million-point matrix.
* **Pipeline:**
    1.  **Raster Ingestion:** Image processing and signal histograms.
    2.  **Vectorization:** Heatmap to Vector conversion.
    3.  **`ChronosAnalyzer` Class:** Object-oriented architecture for processing.
    4.  **Business Intelligence:** Automatic generation of reports with areas ($m^2$) and excavation coordinates.

---

## 📊 Visual Results

The system is capable of transforming raw and noisy data into clean floor plans:

| Raw Data (GPR Simulation) | AI Detection (DBSCAN) | Final Plan (Vectorized) |
|:---:|:---:|:---:|
| *Mixed Noise and Signal* | *3D Clustering* | *Identified Structures* |
| (Insert Heatmap image) | (Insert Plotly image) | (Insert Plan image) |

> *Example: The system filtered 95% of geological noise and identified the Latin Cross plan of the simulated basilica.*

---

## 🚀 How to Run

This project was developed to run on **Google Colab** or **Jupyter Notebook**.

### Prerequisites
```bash
pip install pandas numpy scikit-learn plotly folium matplotlib
```

---

## 👨‍💻 Author

**Isaac Davi** *Developer*

Built as a portfolio project exploring the intersection of **History** and **Technology**.  
Feel free to reach out for collaborations or questions.

---

## 📄 License

This project is intended for **academic and educational purposes**.

* **Free to use:** You may modify and distribute this code for learning and research.
* **Synthetic Data:** Please note that the archaeological data generated in this pipeline is **simulated** (procedural generation) and does not represent real protected sites.

---
