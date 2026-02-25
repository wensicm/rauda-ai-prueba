import csv
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ticket_evaluator.csv_io import read_rows, write_rows
from ticket_evaluator.schemas import parse_llm_json


class EvaluateTicketsTests(unittest.TestCase):
    def test_read_rows_loads_ticket_and_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "tickets.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticket", "reply"])
                writer.writeheader()
                writer.writerow({"ticket": "Need invoice", "reply": "Use billing section"})

            rows = read_rows(csv_path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ticket"], "Need invoice")
            self.assertEqual(rows[0]["reply"], "Use billing section")

    def test_write_rows_creates_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "tickets_evaluated.csv"
            rows = [
                {
                    "ticket": "Cannot login",
                    "reply": "Reset password from login page",
                    "content_score": "4",
                    "content_explanation": "Relevant but could include expected reset email time.",
                    "format_score": "5",
                    "format_explanation": "Clear and concise wording.",
                }
            ]

            write_rows(csv_path, rows)

            with csv_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                loaded = list(reader)

            self.assertEqual(
                reader.fieldnames,
                [
                    "ticket",
                    "reply",
                    "content_score",
                    "content_explanation",
                    "format_score",
                    "format_explanation",
                ],
            )
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["content_score"], "4")

    def test_write_rows_can_include_metadata_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "tickets_evaluated.csv"
            rows = [
                {
                    "ticket": "Cannot login",
                    "reply": "Reset password from login page",
                    "content_score": "3",
                    "content_explanation": "INFRA_ERROR: timeout",
                    "format_score": "3",
                    "format_explanation": "INFRA_ERROR: timeout",
                    "evaluation_status": "infra_error",
                    "evaluation_error": "timeout",
                }
            ]

            write_rows(csv_path, rows, include_metadata=True)

            with csv_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                loaded = list(reader)

            self.assertEqual(
                reader.fieldnames,
                [
                    "ticket",
                    "reply",
                    "content_score",
                    "content_explanation",
                    "format_score",
                    "format_explanation",
                    "evaluation_status",
                    "evaluation_error",
                ],
            )
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["evaluation_status"], "infra_error")

    def test_parse_llm_json_validates_schema(self) -> None:
        parsed = parse_llm_json(
            {
                "content_score": 5,
                "content_explanation": "Fully addresses the request.",
                "format_score": 4,
                "format_explanation": "Clear but a bit wordy.",
            }
        )
        self.assertEqual(parsed["content_score"], "5")
        self.assertEqual(parsed["format_score"], "4")

        with self.assertRaises(ValueError):
            parse_llm_json(
                {
                    "content_score": 7,
                    "content_explanation": "Invalid score should fail.",
                    "format_score": 4,
                    "format_explanation": "Valid format score.",
                }
            )


if __name__ == "__main__":
    unittest.main()
