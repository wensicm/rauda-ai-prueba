"""Evaluate support-ticket replies with an LLM and export scored results.

Usage:
    python -m ticket_evaluator.evaluate_tickets --input tickets.csv --output tickets_evaluated.csv

Environment:
    OPENAI_API_KEY: OpenAI API key used for scoring requests.
"""

import argparse
import os
from pathlib import Path
from typing import Optional

from .csv_io import read_rows, write_rows
from .scoring import evaluate_rows

try:
    from openai import OpenAI, OpenAIError
except Exception:
    OpenAI = None
    OpenAIError = Exception


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate support-ticket replies using an LLM")
    parser.add_argument("--input", default="tickets.csv", help="Input CSV path")
    parser.add_argument("--output", default="tickets_evaluated.csv", help="Output CSV path")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model name")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional max number of rows to process (0 = all)",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries for transient API errors",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=256,
        help="Max output tokens for each LLM response (structured JSON is very compact).",
    )
    parser.add_argument(
        "--store",
        action="store_true",
        help="Persist response bodies on the API side (disabled by default).",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Run without calling OpenAI API (for dry-run; output will contain infrastructure-error rows).",
    )
    parser.add_argument(
        "--error-score",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=3,
        help="Score assigned when evaluation fails due to infrastructure/input issues (default: 3).",
    )
    parser.add_argument(
        "--include-metadata-columns",
        action="store_true",
        help="Include evaluation_status/evaluation_error columns in output CSV.",
    )
    return parser.parse_args()


def evaluate_tickets(
    input_csv: str = "tickets.csv",
    output_csv: str = "tickets_evaluated.csv",
    model: str = "gpt-4o",
    max_rows: int = 0,
    request_timeout: float = 60.0,
    max_retries: int = 3,
    max_output_tokens: int = 256,
    store: bool = False,
    skip_api: bool = False,
    error_score: int = 3,
    include_metadata_columns: bool = False,
) -> str:
    input_path = Path(input_csv)
    output_path = Path(output_csv)

    rows = read_rows(input_path)
    if max_rows and max_rows > 0:
        rows = rows[:max_rows]

    api_key = os.getenv("OPENAI_API_KEY")

    client: Optional[OpenAI]
    if not skip_api:
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK is not available in this environment.")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY no está definida. Expórtala en tu terminal antes de ejecutar."
            )
        client = OpenAI(api_key=api_key)
    else:
        client = None
        print("skip_api=True: running without API calls.")

    evaluated, status_counts = evaluate_rows(
        rows=rows,
        client=client,
        openai_error_type=OpenAIError,
        model=model,
        timeout=request_timeout,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
        store=store,
        error_score=error_score,
    )
    write_rows(
        output_path,
        evaluated,
        include_metadata=include_metadata_columns,
    )

    total = len(evaluated)
    ok_count = status_counts.get("ok", 0)
    infra_count = status_counts.get("infra_error", 0)
    input_count = status_counts.get("input_error", 0)
    print(f"Saved {total} evaluated rows to: {output_path}")
    if infra_count or input_count:
        print(
            "Non-OK rows summary: "
            f"ok={ok_count}, infra_error={infra_count}, input_error={input_count}."
        )

    return str(output_path)


def main() -> None:
    args = parse_args()
    evaluate_tickets(
        input_csv=args.input,
        output_csv=args.output,
        model=args.model,
        max_rows=args.max_rows,
        request_timeout=args.request_timeout,
        max_retries=args.max_retries,
        max_output_tokens=args.max_output_tokens,
        store=args.store,
        skip_api=args.skip_api,
        error_score=args.error_score,
        include_metadata_columns=args.include_metadata_columns,
    )


if __name__ == "__main__":
    main()
