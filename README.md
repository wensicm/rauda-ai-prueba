# Rauda AI - Evaluación automática de respuestas (Ticket LLM)

Este proyecto permite evaluar respuestas de soporte con un modelo de IA y generar `tickets_evaluated.csv` con 4 columnas nuevas:

- `content_score`
- `content_explanation`
- `format_score`
- `format_explanation`


## 0) Qué necesitas

- Python 3.12
- Archivo `tickets.csv` en la carpeta del proyecto
- `OPENAI_API_KEY` (en `.env.example` o exportada en la terminal)

## 1) Entra al proyecto

```bash
cd /TU_RUTA_A/rauda-ai-prueba
```

## 1.5) Pon tu clave API en `.env.example`

## 2) Configuración en un solo comando

```bash
./QUICK_START_KERNEL.sh
```

Este script hace 3 cosas:

1. Crea `./lib`.
2. Instala las librerías necesarias en `./lib`.
3. Registra el kernel `Python (Rauda AI)` para Jupyter.

Además usa `./.env.example` como base para copiar `./lib/.env` si no existe.

## 3) Abrir y usar Jupyter Notebook (la forma más fácil)

1. Abre `evaluate_tickets.ipynb`.
2. Si no ves el Kernel `Python (Rauda AI)` reinicia VS Code: `Developer: Reload Window`.
3. En el selector de kernel elige **Python (Rauda AI)** (es un **Jupyter kernel**, no un entorno Python normal).
4. Ejecuta todas las celdas.

Eso es todo para generar `tickets_evaluated.csv`.

Si no tienes clave, la celda final te lo avisará de forma clara (sin stacktrace) y te dirá cómo continuar.

## 4) Si quieres usar la terminal (opcional)

```bash
python evaluate_tickets.py --input tickets.csv --output tickets_evaluated.csv
```

Opciones útiles:

- `--model` (por defecto `gpt-4o`)
- `--max-rows` (0 = todas)
- `--max-output-tokens` (por defecto `256`, para limitar el JSON estructurado y ahorrar coste)
- `--request-timeout`
- `--max-retries`
- `--skip-store` (no guarda respuestas del LLM en OpenAI)
- `--skip-api` (si quieres forzar ejecución sin llamar a OpenAI; en ese caso se guarda `ERROR` en las explicaciones)

La ejecución usa `OpenAI Responses API` con salida estructurada (`text.format` + `json_schema` con `strict: true`) y validación con `TicketEvaluation` de Pydantic para exigir las 4 claves exactas.

## 5) Resultado esperado

El archivo `tickets_evaluated.csv` tendrá estas columnas:

- `ticket`
- `reply`
- `content_score`
- `content_explanation`
- `format_score`
- `format_explanation`

Las puntuaciones van de 1 a 5.

