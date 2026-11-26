"""ETL de vinhos para o módulo bônus.

Execute na raiz do repositório: ``python -m lab.bonus_module.pipeline``.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from lab.eda_module.analysis import missing_values_report, rating_stats_by_variety
from lab.pandas_module.transformations import clean_ratings, load_wines


DEFAULT_INPUT = Path("lab/data/train_sample.csv")
DEFAULT_OUTPUT = Path("lab/outputs/bonus")
REQUIRED_COLUMNS = {"name", "region", "variety", "rating", "notes"}


def _markdown_cell(value: object) -> str:
    text = re.sub(r"([\\`*_\[\]()!|~])", r"\\\1", str(value))
    text = html.escape(text, quote=False)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def run_pipeline(input_path: Path, output_dir: Path = DEFAULT_OUTPUT) -> None:
    """Leia, valide e agregue os vinhos, produzindo CSV e relatório Markdown."""
    csv_path = output_dir / "summary.csv"
    markdown_path = output_dir / "summary.md"
    if input_path.resolve() in (csv_path.resolve(), markdown_path.resolve()):
        raise ValueError("O arquivo de entrada não pode ser uma saída do ETL.")

    for path in (csv_path, markdown_path):
        path.unlink(missing_ok=True)

    if not input_path.is_file():
        raise ValueError(f"Arquivo de entrada não encontrado: {input_path}")
    try:
        wines = load_wines(str(input_path))
    except pd.errors.EmptyDataError as exc:
        raise ValueError("O arquivo de entrada está vazio.") from exc

    missing_columns = REQUIRED_COLUMNS.difference(wines.columns)
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(missing_columns))}")
    if wines.empty:
        raise ValueError("O arquivo de entrada não contém registros.")

    input_count = len(wines)
    print(f"Linhas lidas: {input_count}")
    print(f"Nulos antes da transformação:\n{missing_values_report(wines)}")

    clean = clean_ratings(wines)
    removed_count = input_count - len(clean)
    print(f"Ratings removidos: {removed_count}")

    clean = clean.copy()
    variety = clean["variety"].astype("string").str.strip()
    missing_variety = variety.isna() | variety.eq("")
    filled_count = int(missing_variety.sum())
    clean["variety"] = variety.mask(missing_variety, "Unknown")
    print(f"Variedades preenchidas com Unknown: {filled_count}")

    if clean.empty:
        raise ValueError("Nenhum registro restou após a limpeza dos ratings.")
    if (
        not pd.api.types.is_numeric_dtype(clean["rating"])
        or clean["rating"].isna().any()
        or not np.isfinite(clean["rating"]).all()
    ):
        raise ValueError("Os ratings devem ser numéricos, não nulos e finitos.")
    if clean["variety"].isna().any() or clean["variety"].eq("").any():
        raise ValueError("As variedades não podem ser nulas ou vazias.")
    print(f"Nulos após a transformação:\n{missing_values_report(clean)}")

    stats = rating_stats_by_variety(clean)
    if "variety" not in stats.columns:
        stats = stats.reset_index()
    summary = (
        stats[["variety", "count", "mean"]]
        .rename(columns={"count": "wine_count", "mean": "avg_rating"})
        .sort_values(["wine_count", "variety"], ascending=[False, True])
        .reset_index(drop=True)
    )
    if summary["wine_count"].sum() != len(clean):
        raise ValueError("A agregação não preservou o total de registros.")
    if summary["variety"].duplicated().any():
        raise ValueError("A agregação contém variedades duplicadas.")
    if not np.isfinite(summary["avg_rating"]).all():
        raise ValueError("A agregação contém médias de rating não finitas.")

    rows = [
        "# Resumo do ETL de vinhos",
        "",
        f"- Linhas lidas: {input_count}",
        f"- Ratings removidos: {removed_count}",
        f"- Variedades preenchidas com Unknown: {filled_count}",
        f"- Linhas após limpeza: {len(clean)}",
        "",
        "| variety | wine_count | avg_rating |",
        "| --- | ---: | ---: |",
    ]
    for row in summary.itertuples(index=False):
        rows.append(f"| {_markdown_cell(row.variety)} | {row.wine_count} | {row.avg_rating:.2f} |")
    markdown = "\n".join(rows) + "\n"

    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        temporary_path = Path(temporary_dir)
        staged_csv = temporary_path / "summary.csv"
        staged_markdown = temporary_path / "summary.md"
        summary.to_csv(staged_csv, index=False, encoding="utf-8")
        staged_markdown.write_text(markdown, encoding="utf-8")
        try:
            staged_csv.replace(csv_path)
            staged_markdown.replace(markdown_path)
        except OSError:
            csv_path.unlink(missing_ok=True)
            markdown_path.unlink(missing_ok=True)
            raise

    print(f"Resumo CSV: {csv_path}")
    print(f"Relatório Markdown: {markdown_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera um resumo de ratings por variedade.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Caminho do CSV de entrada.")
    args = parser.parse_args()
    try:
        run_pipeline(args.input)
    except (ValueError, OSError, pd.errors.ParserError) as exc:
        print(f"Erro no ETL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
