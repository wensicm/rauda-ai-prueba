# Rauda AI - Evaluación automática de respuestas (Ticket LLM)

Este proyecto evalúa respuestas de soporte y genera `tickets_evaluated.csv` con 4 columnas nuevas:

- `content_score`
- `content_explanation`
- `format_score`
- `format_explanation`

## Requisitos

- Python 3.12
- Archivo `tickets.csv` en la raíz del proyecto

## Setup recomendado (estándar)

```bash
cd /TU_RUTA_A/rauda-ai-prueba
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export OPENAI_API_KEY=tu_clave
```

## Ejecutar desde terminal

```bash
python -m ticket_evaluator.evaluate_tickets --input tickets.csv --output tickets_evaluated.csv
```

Opciones útiles:

- `--model` (por defecto `gpt-4o`)
- `--max-rows` (0 = todas)
- `--max-output-tokens` (por defecto `256`)
- `--request-timeout`
- `--max-retries`
- `--store` (opcional: guarda respuestas en OpenAI; por defecto `False`)
- `--skip-api` (ejecución sin llamadas API; deja filas marcadas como error técnico)
- `--error-score` (score para errores técnicos/infra; por defecto `3`)
- `--include-metadata-columns` (añade `evaluation_status` y `evaluation_error` al CSV)

## Notebook (opcional)

También puedes ejecutar `evaluate_tickets.ipynb` usando el mismo `.venv`.

## Tests (opcionales)

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Estos tests cubren tres validaciones básicas:

- Lectura de `tickets.csv` (`read_rows`) con columnas requeridas (`ticket`, `reply`).
- Escritura de `tickets_evaluated.csv` (`write_rows`) con el orden de columnas esperado.
- Escritura opcional de metadatos (`evaluation_status`, `evaluation_error`).
- Validación de salida estructurada (`parse_llm_json`) para aceptar schema correcto y rechazar scores fuera de rango.

## Resultado esperado

`tickets_evaluated.csv` incluye:

- `ticket`
- `reply`
- `content_score`
- `content_explanation`
- `format_score`
- `format_explanation`

Los scores van de 1 a 5.

La evaluación usa `OpenAI Responses API` con salida estructurada (`text.format` + `json_schema` con `strict: true`) y validación con Pydantic.

## Notas de robustez

- Dependencias críticas están declaradas explícitamente en `requirements.txt` (`openai`, `pydantic`).
- Errores de infraestructura no se silencian: quedan marcados con prefijo `INFRA_ERROR` y puedes exportar metadatos con `--include-metadata-columns`.
- El código está separado por responsabilidad:
  - `ticket_evaluator/evaluate_tickets.py`: orquestación y CLI.
  - `ticket_evaluator/csv_io.py`: lectura/escritura de CSV.
  - `ticket_evaluator/scoring.py`: evaluación con LLM y manejo de errores por fila.
  - `ticket_evaluator/schemas.py`: schema estricto y parsing.
