"""Verificações do ETL do módulo bônus."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from lab.bonus_module.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "lab/data/train_sample.csv"


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_dir.cleanup)
        self.directory = Path(self.temporary_dir.name)
        self.output_dir = self.directory / "output"

    def run_etl(self, input_path: Path) -> str:
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            run_pipeline(input_path, self.output_dir)
        return log.getvalue()

    def test_sample_and_reproducibility(self) -> None:
        log = self.run_etl(SAMPLE)
        csv_path = self.output_dir / "summary.csv"
        markdown_path = self.output_dir / "summary.md"
        first_csv = csv_path.read_bytes()
        first_markdown = markdown_path.read_bytes()
        summary = pd.read_csv(csv_path)

        self.assertIn("Linhas lidas: 1000", log)
        self.assertIn("Ratings removidos: 0", log)
        self.assertIn("Variedades preenchidas com Unknown: 11", log)
        self.assertEqual(list(summary.columns), ["variety", "wine_count", "avg_rating"])
        self.assertEqual(len(summary), 9)
        self.assertEqual(summary["wine_count"].sum(), 1000)
        unknown = summary.loc[summary["variety"] == "Unknown"].iloc[0]
        self.assertEqual(unknown["wine_count"], 11)
        expected_mean = pd.read_csv(SAMPLE).loc[lambda df: df["variety"].isna(), "rating"].mean()
        self.assertAlmostEqual(unknown["avg_rating"], expected_mean)
        self.assertIn("| Unknown | 11 | 92.00 |", first_markdown.decode("utf-8"))
        self.run_etl(SAMPLE)
        self.assertEqual(csv_path.read_bytes(), first_csv)
        self.assertEqual(markdown_path.read_bytes(), first_markdown)

    def test_cleaning_blanks_invalid_ratings_and_markdown(self) -> None:
        input_path = self.directory / "input.csv"
        pd.DataFrame(
            {
                "name": ["a", "b", "c", "d"],
                "region": ["r"] * 4,
                "variety": ["  ", None, "  A|B  ", "ignored"],
                "rating": ["80", "90", "100", "invalid"],
                "notes": [None] * 4,
            }
        ).to_csv(input_path, index=False)
        log = self.run_etl(input_path)
        summary = pd.read_csv(self.output_dir / "summary.csv")
        self.assertIn("Ratings removidos: 1", log)
        self.assertIn("Variedades preenchidas com Unknown: 2", log)
        self.assertEqual(summary["variety"].tolist(), ["Unknown", "A|B"])
        self.assertEqual(summary["wine_count"].tolist(), [2, 1])
        self.assertIn(r"| A\|B | 1 | 100.00 |", (self.output_dir / "summary.md").read_text())

    def test_invalid_inputs_remove_previous_results(self) -> None:
        cases = [
            ("name,region,variety,notes\na,r,v,n\n", "rating"),
            ("name,region,variety,rating,notes\n", "não contém registros"),
            ("", "está vazio"),
            ("name,region,variety,rating,notes\na,r,v,invalid,n\n", "Nenhum registro"),
            ("name,region,variety,rating,notes\na,r,v,inf,n\n", "finitos"),
        ]
        input_path = self.directory / "invalid.csv"
        for contents, message in cases:
            with self.subTest(message=message):
                self.run_etl(SAMPLE)
                input_path.write_text(contents, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    self.run_etl(input_path)
                self.assertFalse((self.output_dir / "summary.csv").exists())
                self.assertFalse((self.output_dir / "summary.md").exists())

    def test_summary_order_precision_and_markdown_escaping(self) -> None:
        input_path = self.directory / "input.csv"
        variety = "A|\\\n**B** <tag>"
        pd.DataFrame(
            {
                "name": ["a", "b", "c", "d"],
                "region": ["r"] * 4,
                "variety": ["Z", "Z", variety, variety],
                "rating": [80, 90, 80, 81],
                "notes": ["n"] * 4,
            }
        ).to_csv(input_path, index=False)
        self.run_etl(input_path)
        summary = pd.read_csv(self.output_dir / "summary.csv")
        self.assertEqual(summary["variety"].tolist(), [variety, "Z"])
        self.assertEqual(summary["wine_count"].tolist(), [2, 2])
        self.assertEqual(summary["avg_rating"].tolist(), [80.5, 85.0])
        markdown = (self.output_dir / "summary.md").read_text(encoding="utf-8")
        self.assertIn(r"A\|\\<br>\*\*B\*\* &lt;tag&gt; | 2 | 80.50 |", markdown)

    def test_aggregation_validation_blocks_export(self) -> None:
        cases = [
            (pd.DataFrame({"variety": ["A"], "count": [1], "mean": [90.0]}), "total"),
            (
                pd.DataFrame({"variety": ["A", "A"], "count": [500, 500], "mean": [90.0, 91.0]}),
                "duplicadas",
            ),
            (pd.DataFrame({"variety": ["A"], "count": [1000], "mean": [float("inf")]}), "finitas"),
        ]
        for stats, message in cases:
            with self.subTest(message=message):
                with patch("lab.bonus_module.pipeline.rating_stats_by_variety", return_value=stats):
                    with self.assertRaisesRegex(ValueError, message):
                        self.run_etl(SAMPLE)
                self.assertFalse((self.output_dir / "summary.csv").exists())
                self.assertFalse((self.output_dir / "summary.md").exists())

    def test_aggregation_with_variety_in_index(self) -> None:
        stats = pd.DataFrame(
            {"count": [1000], "mean": [91.123456], "min": [80], "max": [100]},
            index=pd.Index(["A"], name="variety"),
        )
        with patch("lab.bonus_module.pipeline.rating_stats_by_variety", return_value=stats):
            self.run_etl(SAMPLE)
        summary = pd.read_csv(self.output_dir / "summary.csv")
        self.assertEqual(summary.loc[0, "avg_rating"], 91.123456)
        markdown = (self.output_dir / "summary.md").read_text(encoding="utf-8")
        self.assertIn("| A | 1000 | 91.12 |", markdown)

    def test_cli_reports_failure_with_nonzero_exit(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "lab.bonus_module.pipeline", "--input", "missing.csv"],
            cwd=self.directory,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Arquivo de entrada não encontrado", result.stderr)

    def test_cli_exports_results(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "lab.bonus_module.pipeline", "--input", str(SAMPLE)],
            cwd=self.directory,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.directory / "lab/outputs/bonus/summary.csv").is_file())
        self.assertTrue((self.directory / "lab/outputs/bonus/summary.md").is_file())


if __name__ == "__main__":
    unittest.main()
