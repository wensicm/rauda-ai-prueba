"""Evaluate support-ticket replies with an LLM and export scored results.

Usage:
    python evaluate_tickets.py --input tickets.csv --output tickets_evaluated.csv

Environment:
    OPENAI_API_KEY: OpenAI API key used for scoring requests.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from pydantic import BaseModel, Field, ValidationError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR
if not (REPO_ROOT / "requirements.txt").exists() and (SCRIPT_DIR.parent / "requirements.txt").exists():
    REPO_ROOT = SCRIPT_DIR.parent
LOCAL_LIB_DIR = REPO_ROOT / "lib"

if str(LOCAL_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_LIB_DIR))

try:
    from openai import OpenAI, OpenAIError
except Exception:
    OpenAI = None
    OpenAIError = Exception

ENV_FILE = LOCAL_LIB_DIR / ".env"
class TicketEvaluation(BaseModel):
    """Strict schema expected from the model output."""

    content_score: int = Field(ge=1, le=5)
    content_explanation: str
    format_score: int = Field(ge=1, le=5)
    format_explanation: str


RESPONSE_SCHEMA_NAME = "ticket_evaluation"
RESPONSE_SCHEMA = TicketEvaluation.model_json_schema()
if "additionalProperties" not in RESPONSE_SCHEMA:
    RESPONSE_SCHEMA["additionalProperties"] = False
if "required" not in RESPONSE_SCHEMA:
    RESPONSE_SCHEMA["required"] = list(TicketEvaluation.model_fields.keys())

RESPONSE_TEXT_FORMAT = {
    "type": "json_schema",
    "name": RESPONSE_SCHEMA_NAME,
    "schema": RESPONSE_SCHEMA,
    "strict": True,
}


def load_local_env(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key.strip(), value)


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
        "--skip-store",
        action="store_true",
        help="Do not persist response bodies on the API side.",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Run without calling OpenAI API (for dry-run; output will contain error rows).",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            reader.fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames]
        rows = list(reader)

    required = {"ticket", "reply"}
    if rows:
        missing = required.difference(rows[0].keys())
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    elif not rows:
        raise ValueError("Input CSV has no rows")

    return rows


def build_messages(ticket: str, reply: str) -> list[dict]:
    system_msg = (
        "You are an evaluator for customer support quality. "
        "Score the reply against the ticket independently on two dimensions: "
        "content and format. Return ONLY strict JSON with keys: "
        "content_score, content_explanation, format_score, format_explanation. "
        "Scores must be integers from 1 to 5. Explanations should be short (1-2 sentences)."
    )
    user_msg = (
        "Evaluate this support pair:\n\n"
        f"Ticket:\n{ticket}\n\n"
        f"Reply:\n{reply}\n\n"
        "Dimensions:\n"
        "1) Content: relevance, correctness, completeness.\n"
        "2) Format: clarity, structure, grammar, and spelling.\n"
        "Return strict JSON only."
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def error_result(reason: str) -> Dict[str, str]:
    msg = f"ERROR: {reason}"
    return {
        "content_score": "1",
        "content_explanation": msg,
        "format_score": "1",
        "format_explanation": msg,
    }


def parse_llm_json(raw: object) -> Dict[str, str]:
    try:
        if isinstance(raw, TicketEvaluation):
            parsed = raw
        elif isinstance(raw, dict):
            parsed = TicketEvaluation.model_validate(raw)
        elif isinstance(raw, str):
            parsed = TicketEvaluation.model_validate_json(raw)
        else:
            parsed = TicketEvaluation.model_validate_json(str(raw or "").strip())
    except (TypeError, ValidationError, ValueError) as exc:
        raise ValueError(f"LLM output did not match expected schema: {exc}")

    return {
        "content_score": str(parsed.content_score),
        "content_explanation": str(parsed.content_explanation)[:1000],
        "format_score": str(parsed.format_score),
        "format_explanation": str(parsed.format_explanation)[:1000],
    }


def extract_output_text(response: Any) -> str:
    if response is None:
        return ""

    output_text = getattr(response, "output_text", "")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    collected: list[str] = []
    output = getattr(response, "output", [])
    if isinstance(output, list):
        for item in output:
            for content in getattr(item, "content", []) or []:
                content_type = getattr(content, "type", None)
                if content_type == "output_text":
                    text = getattr(content, "text", "")
                    if isinstance(text, dict):
                        text = text.get("value", "")
                    if isinstance(text, str):
                        collected.append(text)
                if content_type == "refusal":
                    text = getattr(content, "refusal", "")
                    if isinstance(text, str):
                        collected.append(text)
    return "".join(collected).strip()


def evaluate_with_llm(
    client: OpenAI,
    model: str,
    ticket: str,
    reply: str,
    timeout: float,
    max_retries: int,
    max_output_tokens: int,
    skip_store: bool,
) -> Dict[str, str]:
    messages = build_messages(ticket, reply)
    if not hasattr(client, "responses"):
        raise RuntimeError(
            "Tu versión del SDK de OpenAI no soporta Responses API. "
            "Actualiza a openai>=1.54 y vuelve a ejecutar QUICK_START_KERNEL.sh."
        )
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=messages,
                text={"format": RESPONSE_TEXT_FORMAT},
                max_output_tokens=max_output_tokens,
                store=not skip_store,
                temperature=0,
                timeout=timeout,
            )
            raw_output = extract_output_text(response)
            if not raw_output:
                raise RuntimeError("LLM response did not contain text output.")
            return parse_llm_json(raw_output)
        except (OpenAIError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == max_retries:
                break
            wait = 2 ** (attempt - 1)
            time.sleep(wait)

    raise RuntimeError(f"LLM evaluation failed after {max_retries} attempts: {last_error}")


def evaluate_row(
    row: dict,
    client: Optional[OpenAI],
    model: str,
    timeout: float,
    max_retries: int,
    max_output_tokens: int,
    skip_store: bool,
) -> Dict[str, str]:
    ticket = (row.get("ticket") or "").strip()
    reply = (row.get("reply") or "").strip()

    if not ticket or not reply:
        return error_result("Missing ticket or reply text; unable to evaluate.")

    if client is None:
        return error_result("OpenAI client not configured (set OPENAI_API_KEY or remove skip_api).")

    try:
        return evaluate_with_llm(
            client=client,
            model=model,
            ticket=ticket,
            reply=reply,
            timeout=timeout,
            max_retries=max_retries,
            max_output_tokens=max_output_tokens,
            skip_store=skip_store,
        )
    except Exception as exc:
        return error_result(f"LLM evaluation failed: {exc}")


def evaluate_rows(
    rows: Iterable[dict],
    client: Optional[OpenAI],
    model: str,
    timeout: float,
    max_retries: int,
    max_output_tokens: int,
    skip_store: bool,
) -> list[dict]:
    evaluated = []
    for row in rows:
        scores = evaluate_row(
            row,
            client=client,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            max_output_tokens=max_output_tokens,
            skip_store=skip_store,
        )
        evaluated.append({**row, **scores})
    return evaluated


def write_rows(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    fieldnames = [
        "ticket",
        "reply",
        "content_score",
        "content_explanation",
        "format_score",
        "format_explanation",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def evaluate_tickets(
    input_csv: str = "tickets.csv",
    output_csv: str = "tickets_evaluated.csv",
    model: str = "gpt-4o",
    max_rows: int = 0,
    request_timeout: float = 60.0,
    max_retries: int = 3,
    max_output_tokens: int = 256,
    skip_store: bool = False,
    skip_api: bool = False,
) -> str:
    input_path = Path(input_csv)
    output_path = Path(output_csv)

    rows = read_rows(input_path)
    if max_rows and max_rows > 0:
        rows = rows[:max_rows]

    load_local_env(ENV_FILE)
    api_key = os.getenv("OPENAI_API_KEY")

    client: Optional[OpenAI]
    if not skip_api:
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK is not available in this environment.")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY no está definida. Configúrala en lib/.env y vuelve a ejecutar."
            )
        client = OpenAI(api_key=api_key)
    else:
        client = None
        print("skip_api=True: running without API calls.")

    evaluated = evaluate_rows(
        rows=rows,
        client=client,
        model=model,
        timeout=request_timeout,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
        skip_store=skip_store,
    )
    write_rows(output_path, evaluated)
    print(f"Saved {len(evaluated)} evaluated rows to: {output_path}")
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
        skip_store=args.skip_store,
        skip_api=args.skip_api,
    )


if __name__ == "__main__":
    main()
