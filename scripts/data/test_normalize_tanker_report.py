
#!/usr/bin/env python3
"""Regression tests for the local Week 43 tanker normalization pipeline."""

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORMALIZER = ROOT / "scripts/data/normalize_tanker_report.py"
VALIDATOR = ROOT / "scripts/data/validate_tanker_candidates.py"

OUT_DIR = ROOT / "data/processed/freight_rates/tanker"
CANDIDATES = OUT_DIR / "tanker_week_43_normalized_candidates.csv"
REPORT = OUT_DIR / "tanker_week_43_normalization_report.json"

EXPECTED_ROWS = 51
EXPECTED_ROUTES = 26
EXPECTED_REVIEW_STATUS = "REVIEW_REQUIRED_SINGLE_WEEK"

ALLOWED_UNITS = {
    "worldscale_assessment": "WS_points",
    "tce_earnings": "USD_per_day",
    "voyage_rate": "USD_per_voyage",
}


class TankerNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, str(NORMALIZER)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def load_candidates(self):
        with CANDIDATES.open(
            encoding="utf-8-sig",
            newline="",
        ) as f:
            return list(csv.DictReader(f))

    def test_expected_dataset_size(self):
        rows = self.load_candidates()

        self.assertEqual(len(rows), EXPECTED_ROWS)
        self.assertEqual(
            len({row["route_code"] for row in rows}),
            EXPECTED_ROUTES,
        )

    def test_no_duplicate_route_metric_pairs(self):
        rows = self.load_candidates()
        keys = [(row["route_code"], row["metric"]) for row in rows]

        self.assertEqual(len(keys), len(set(keys)))

    def test_report_is_local_only_and_portable(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertEqual(report["mode"], "LOCAL_NORMALIZATION_ONLY")
        self.assertIs(report["supabase_writes"], False)
        self.assertEqual(report["review_status"], EXPECTED_REVIEW_STATUS)
        self.assertEqual(report["route_count"], EXPECTED_ROUTES)
        self.assertEqual(report["metric_observation_rows"], EXPECTED_ROWS)
        self.assertEqual(
            report["output_file"],
            "data/processed/freight_rates/tanker/"
            "tanker_week_43_normalized_candidates.csv",
        )

    def test_outputs_are_repeatable(self):
        before = (CANDIDATES.read_bytes(), REPORT.read_bytes())

        subprocess.run(
            [sys.executable, str(NORMALIZER)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        after = (CANDIDATES.read_bytes(), REPORT.read_bytes())

        self.assertEqual(before, after)

    def test_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("Errors: 0", result.stdout)
        self.assertIn("Numeric token review flags: 0", result.stdout)
        self.assertIn("PASS:", result.stdout)

    def test_metric_units_are_consistent(self):
        rows = self.load_candidates()

        for row in rows:
            with self.subTest(
                route=row["route_code"],
                metric=row["metric"],
            ):
                self.assertIn(row["metric"], ALLOWED_UNITS)
                self.assertEqual(
                    row["unit"],
                    ALLOWED_UNITS[row["metric"]],
                )

    def test_populated_weekly_changes_have_metadata(self):
        rows = self.load_candidates()

        for row in rows:
            if row["weekly_change_value"].strip():
                with self.subTest(
                    route=row["route_code"],
                    metric=row["metric"],
                ):
                    self.assertTrue(row["weekly_change_unit"].strip())
                    self.assertTrue(
                        row["weekly_change_qualifier"].strip()
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
