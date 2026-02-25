"""Structured output schema and parsing helpers."""

from typing import Dict

from pydantic import BaseModel, Field, ValidationError


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


def parse_llm_json(raw: object) -> Dict[str, str]:
    """Validate and normalize model output."""
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
