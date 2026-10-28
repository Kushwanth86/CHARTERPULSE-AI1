
#!/usr/bin/env python3
"""Regression tests for the local Week 43 tanker normalization pipeline."""

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/data"))
from validate_tanker_candidates import route_context, token_found

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


    def test_route_context_excludes_neighboring_route_values(self):
        paragraph = (
            "The TC1 index climbed by 92 points to WS1075. "
            "For the TC20 run, the index edged up by $168,800 to $21.51 million."
        )
        tc1 = route_context(paragraph, "TC1")
        tc20 = route_context(paragraph, "TC20")

        self.assertIn("WS1075", tc1)
        self.assertNotIn("21.51 million", tc1)
        self.assertIn("21.51 million", tc20)
        self.assertNotIn("WS1075", tc20)

    def test_route_context_keeps_decimal_worldscale_values_intact(self):
        paragraph = (
            "The TD3C route dropped 88 points to WS1,208.13, "
            "giving a daily TCE of $1,287,851."
        )
        context = route_context(paragraph, "TD3C")

        self.assertIn("WS1,208.13", context)
        self.assertTrue(token_found(context, "1208.13", "worldscale_assessment"))

    def test_route_context_includes_following_tce_sentence(self):
        paragraph = (
            "In the Mediterranean, the TC6 index climbed by 72 points to WS526. "
            "The corresponding Baltic round-trip TCE rose by $20,700 to $109,600/day. "
            "The TC23 index gained 71 points to WS390."
        )
        tc6 = route_context(paragraph, "TC6")

        self.assertIn("$109,600/day", tc6)
        self.assertNotIn("TC23", tc6)
        self.assertTrue(token_found(tc6, "109600", "tce_earnings"))

    def test_route_context_missing_route_returns_empty_string(self):
        self.assertEqual(route_context("The TC1 index rose.", "TD3C"), "")

    def test_numeric_token_matching_rejects_substrings(self):
        self.assertFalse(token_found("The assessment was 312 points.", "12", "worldscale_assessment"))
        self.assertFalse(token_found("The assessment was 12.5 points.", "12", "worldscale_assessment"))
        self.assertFalse(token_found("The assessment was WS10750.", "1075", "worldscale_assessment"))

    def test_numeric_token_matching_accepts_formatted_values(self):
        self.assertTrue(token_found("The assessment reached WS1,208.13.", "1208.13", "worldscale_assessment"))
        self.assertTrue(token_found("The rate reached $21.51 million.", "21510000", "voyage_rate"))
        self.assertTrue(token_found("TCE reached $109,600/day.", "109600", "tce_earnings"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
