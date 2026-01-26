# Chronos-AI

Sistema de IA para Descoberta Arqueológica. Usa Aprendizado Não Supervisionado (DBSCAN) e Visão Computacional para detectar estruturas enterradas em dados simulados de GPR/LIDAR. Inspirado em pesquisas não invasivas do Vaticano. 🇧🇷

## Estrutura do Projeto

```
Chronos-AI/
│
├── README.md           # Documentação em Inglês
├── README.pt-br.md     # Documentação em Português
│
├── notebooks/          # Pasta principal dos códigos
│   ├── en/             # Versão em Inglês
│   │   └── ...
│   │
│   └── pt-br/          # Versão em Português
│       └── ...
│
├── data/               # CSVs e Datasets (comuns aos dois idiomas)
│   └── ...
│
└── requirements.txt    # Bibliotecas necessárias
```

## Sobre o Projeto

Chronos-AI é um sistema de inteligência artificial desenvolvido para auxiliar em descobertas arqueológicas através de análise de dados de GPR (Ground Penetrating Radar) e LIDAR. O sistema utiliza técnicas de aprendizado não supervisionado, especialmente o algoritmo DBSCAN, juntamente com visão computacional para identificar estruturas enterradas de forma não invasiva.

## Instalação

```bash
pip install -r requirements.txt
```

## Como Usar

Os notebooks estão organizados por idioma:
- `notebooks/pt-br/`: Notebooks em Português
- `notebooks/en/`: Notebooks em Inglês

Os datasets estão localizados na pasta `data/` e são compartilhados entre as duas versões.

## Licença

Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
