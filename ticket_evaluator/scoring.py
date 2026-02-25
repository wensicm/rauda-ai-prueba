"""LLM scoring logic for ticket replies."""

import json
import time
from typing import Any, Dict, Iterable, Optional

from .schemas import RESPONSE_TEXT_FORMAT, parse_llm_json


def build_messages(ticket: str, reply: str) -> list[dict]:
    system_msg = (
        "You are a strict evaluator for customer support replies. "
        "Score the reply against the ticket on two independent dimensions: Content and Format. "
        "Use the full integer scale 1, 2, 3, 4, 5 (do not collapse to only 1/3/5):\n"
        "Content 1: irrelevant, incorrect, or missing the key request.\n"
        "Content 2: mostly incorrect or missing major required details.\n"
        "Content 3: partially helpful but incomplete or ambiguous.\n"
        "Content 4: mostly correct and relevant, with minor omissions.\n"
        "Content 5: fully relevant, correct, complete, and actionable.\n"
        "Format 1: confusing, disorganized, unprofessional, or major grammar issues.\n"
        "Format 2: understandable with significant clarity/structure/language issues.\n"
        "Format 3: understandable with minor clarity/structure/grammar issues.\n"
        "Format 4: clear and well-structured, with only small style issues.\n"
        "Format 5: clear, concise, well-structured, professional, and grammatically clean.\n"
        "When a score is below 5, explicitly mention the most important missing or incorrect point.\n"
        "Borderline examples:\n"
        "- Ticket: 'How do I reset my password?' Reply: 'Use Forgot Password and follow the email link.' "
        "-> usually Content 5, Format 5.\n"
        "- Ticket: 'Send me last month's invoice.' Reply: 'Please contact support.' "
        "-> low Content due to missing concrete steps/account guidance.\n"
        "Return ONLY strict JSON with keys: content_score, content_explanation, format_score, format_explanation. "
        "Scores must be integers from 1 to 5; explanations must be 1-2 short sentences."
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


def error_result(reason: str, error_score: int, status: str) -> Dict[str, str]:
    if status == "infra_error":
        prefix = "INFRA_ERROR"
    elif status == "input_error":
        prefix = "INPUT_ERROR"
    else:
        prefix = "ERROR"

    msg = f"{prefix}: {reason}"
    score = str(error_score)
    return {
        "content_score": score,
        "content_explanation": msg,
        "format_score": score,
        "format_explanation": msg,
        "evaluation_status": status,
        "evaluation_error": reason,
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
    client: Any,
    openai_error_type: type[Exception],
    model: str,
    ticket: str,
    reply: str,
    timeout: float,
    max_retries: int,
    max_output_tokens: int,
    store: bool,
) -> Dict[str, str]:
    messages = build_messages(ticket, reply)
    if not hasattr(client, "responses"):
        raise RuntimeError(
            "Tu versión del SDK de OpenAI no soporta Responses API. "
            "Actualiza a openai>=1.54 e instala dependencias con pip install -r requirements.txt."
        )
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=messages,
                text={"format": RESPONSE_TEXT_FORMAT},
                max_output_tokens=max_output_tokens,
                store=store,
                temperature=0,
                timeout=timeout,
            )
            raw_output = extract_output_text(response)
            if not raw_output:
                raise RuntimeError("LLM response did not contain text output.")
            parsed = parse_llm_json(raw_output)
            return {
                **parsed,
                "evaluation_status": "ok",
                "evaluation_error": "",
            }
        except (openai_error_type, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == max_retries:
                break
            wait = 2 ** (attempt - 1)
            time.sleep(wait)

    raise RuntimeError(f"LLM evaluation failed after {max_retries} attempts: {last_error}")


def evaluate_row(
    row: dict,
    client: Optional[Any],
    openai_error_type: type[Exception],
    model: str,
    timeout: float,
    max_retries: int,
    max_output_tokens: int,
    store: bool,
    error_score: int,
) -> Dict[str, str]:
    ticket = (row.get("ticket") or "").strip()
    reply = (row.get("reply") or "").strip()

    if not ticket or not reply:
        return error_result(
            reason="Missing ticket or reply text; unable to evaluate.",
            error_score=error_score,
            status="input_error",
        )

    if client is None:
        return error_result(
            reason="OpenAI client not configured (set OPENAI_API_KEY or remove skip_api).",
            error_score=error_score,
            status="infra_error",
        )

    try:
        return evaluate_with_llm(
            client=client,
            openai_error_type=openai_error_type,
            model=model,
            ticket=ticket,
            reply=reply,
            timeout=timeout,
            max_retries=max_retries,
            max_output_tokens=max_output_tokens,
            store=store,
        )
    except Exception as exc:
        return error_result(
            reason=f"LLM evaluation failed: {exc}",
            error_score=error_score,
            status="infra_error",
        )


def evaluate_rows(
    rows: Iterable[dict],
    client: Optional[Any],
    openai_error_type: type[Exception],
    model: str,
    timeout: float,
    max_retries: int,
    max_output_tokens: int,
    store: bool,
    error_score: int,
) -> tuple[list[dict], Dict[str, int]]:
    evaluated: list[dict] = []
    status_counts: Dict[str, int] = {}
    for row in rows:
        scores = evaluate_row(
            row=row,
            client=client,
            openai_error_type=openai_error_type,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            max_output_tokens=max_output_tokens,
            store=store,
            error_score=error_score,
        )
        status = str(scores.get("evaluation_status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        evaluated.append({**row, **scores})
    return evaluated, status_counts
