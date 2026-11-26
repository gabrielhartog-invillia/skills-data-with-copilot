"""Módulo 4 — Visualização de Dados.

Complete cada função com o apoio do GitHub Copilot. Cada função deve **gerar um
gráfico e salvá-lo** no caminho ``out_path`` (formato PNG). Use ``matplotlib`` e
``seaborn``. Em ambientes sem interface gráfica (CI), mantenha o backend "Agg".

Valide com:  ``python lab/check.py --module viz``
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # backend sem interface gráfica (funciona no CI)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402


def plot_rating_distribution(df: pd.DataFrame, out_path: str):
    """Histograma da distribuição da coluna ``rating``. Inclua título e labels em
    português e salve a figura em ``out_path``."""
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(data=df, x="rating", bins=20, ax=ax)
    ax.set_title("Distribuição das notas")
    ax.set_xlabel("Nota")
    ax.set_ylabel("Quantidade")
    fig.tight_layout()
    fig.savefig(out_path, format="png")
    plt.close(fig)


def plot_top_varieties(df: pd.DataFrame, out_path: str):
    """Gráfico de barras horizontais com as 10 variedades (``variety``) com maior
    quantidade de vinhos. Salve a figura em ``out_path``."""
    counts = df["variety"].value_counts().head(10).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(x=counts.values, y=counts.index, ax=ax)
    ax.set_title("10 variedades mais frequentes")
    ax.set_xlabel("Quantidade de vinhos")
    ax.set_ylabel("Variedade")
    fig.tight_layout()
    fig.savefig(out_path, format="png")
    plt.close(fig)


def plot_boxplot_by_variety(df: pd.DataFrame, out_path: str):
    """Boxplot de ``rating`` para as 5 variedades mais frequentes. Salve a figura
    em ``out_path``."""
    top_varieties = df["variety"].value_counts().head(5).index
    df_top = df[df["variety"].isin(top_varieties)]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=df_top, x="variety", y="rating", ax=ax)
    ax.set_title("Distribuição das notas por variedade (top 5)")
    ax.set_xlabel("Variedade")
    ax.set_ylabel("Nota")
    fig.tight_layout()
    fig.savefig(out_path, format="png")
    plt.close(fig)
