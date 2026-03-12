# AGENTS Maestro - C:\Users\wencm\Desktop\Repositorios

## Alcance
Estas instrucciones son de cumplimiento obligatorio para todos los repositorios bajo `C:\Users\wencm\Desktop\Repositorios`.

## Reglas comunes a todos los repositorios
- No guardar en GitHub identidades de cuenta (`arn:...`), credenciales, claves API, tokens ni secretos.
- Antes de crear o modificar recursos de AWS (SSM, IAM, S3, ECS, etc.), pide explícitamente permiso al usuario.
- No ejecutes acciones sensibles de AWS sin confirmación explícita del usuario, aunque existan credenciales disponibles.
- En tareas largas con alta probabilidad de durar más de 5 minutos (entrenamiento, generación masiva de features, inferencia completa, etc.), implementa checkpoints persistentes y capacidad de reanudación (`resume`) para recuperar tras apagados/interrupciones.
- Usa siempre Python 3.12.
- Si instalas librerías en este entorno, hazlo dentro de la carpeta `lib` del repositorio correspondiente.
- Mantén en `.gitignore` (cuando aplique) reglas para proteger archivos sensibles y entorno:
  - `lib/`
  - `*.env`, `.env.*`, `.env`
  - `*.key`, `*.pem`, `*.p12`
  - `*.secret`, `*secret*`
  - `credentials*`, `config*secret*`, `*token*`, `kaggle.json`, `openai_api_key.json`
- Usa siempre la documentación oficial de OpenAI para trabajo con OpenAI/Codex, y no hace falta que el usuario lo pida cada vez.
  - MCP disponible: `openaiDeveloperDocs`
  - MCP disponible: `aws-mcp` (AWS MCP Server vía `mcp-proxy-for-aws`, región por defecto `eu-west-1`).

## Política de rama (obligatoria)
- Trabaja siempre en la rama `SurfacePro`.
- Antes de editar, crear o cambiar explícitamente a `SurfacePro`.
- Los cambios de código y sus commits se realizan en `SurfacePro`.
- cada vez que cambies código haz commits en el repo con la rama `SurfacePro`

## Reglas de sincronización de AGENTS (obligatorias)
- Si se añade nueva información a cualquier `AGENTS.md` de un proyecto, esa información debe integrarse en la sección adecuada del presente documento y propagarse al resto de `AGENTS.md` de todos los repositorios bajo `C:\Users\wencm\Desktop\Repositorios`.
- Mantener sincronizados entre sí todos los `AGENTS.md` de esta jerarquía.

## Secciones especializadas de Eris/Shipd
Estas instrucciones proceden de `Eris/AGENTS.md` y se mantienen para cuando trabajemos con retos tipo Shipd/ML que comparten este flujo.
- Estas instrucciones aplican a proyectos de este repositorio con formato de competición tipo `shipd-eris`.
- Shipd.ai es una plataforma de retos de Machine Learning y Data Science; cada subcarpeta es un reto/mini-competición/proyecto.
- El usuario copiará instrucciones de cada competición y estas deben incluirse en un `README.md` dentro de cada proyecto.
- Eris gira alrededor de `datasets`, `challenges`, `solutions` y `rubrics`.
- Asumir por defecto que el runtime del reto se parece a Kaggle Docker: priorizar librerías comunes del stack y evitar dependencias exóticas sin beneficio claro.
- En retos de solver, las entregas deben ser autocontenidas, rutas relativas desde raíz, leer desde `./dataset/public/` y escribir `./working/submission.csv`.
- Al crear/revisar challenge: `prepare.py` debe ser determinista y producir splits reproducibles; `grade.py` robusto en validación y edge cases.
- En Shipd/Eris, `submissions` consumen créditos por envío. Patrón observado: `6` créditos máximos por problema y recarga de `1` crédito cada `4h`.
- Para premios de solver, priorizar soluciones que superen el AI baseline.
- Los challenges cierran con `10` solvers evaluados y luego 24h de countdown.
- Las rubrics deben ser específicas, medibles y discriminantes.
- Estados de plataforma: `Draft`, `Pending`, `Changes`, `Accepted`, `Rejected`.
- Si se inspira contenido de Kaggle: no copiar competiciones; reutilizar datasets públicos con licencia compatible y señalar dudas legales/compliance.
- Hardware sugerido:
  - Si el stack lo soporta, priorizar entrenamiento/inferencia con GPU `NVIDIA GeForce RTX 3050 Laptop GPU`.
  - Si un reto/proyecto requiere cómputo, priorizar Google Colab.
  - Si Colab está ocupado y la GPU local también, no lanzar una tercera carga concurrente.
- Flujo web de Shipd:
  - Preferir `Playwright MCP` y reutilizar sesión/pestaña activa cuando exista.
  - Si hay login, intentar primero Google.
  - En subida de archivos desde Playwright, si falla por ruta, se permite servidor HTTP local temporal para inyectar `solution.py` y `working/submission.csv`.
  - Tras iteraciones, mantener el repo con la mejor variante enviada.
- Playwright en WSL:
  - Usar `Chromium` de `Ubuntu/WSL`.
  - Reutilizar instancia abierta antes de abrir una nueva.
  - Cada agente en su pestaña.
  - Mantener Chromium vivo desacoplado del shell.
- Entorno Python:
  - Usar `uv` para entornos e instalación.
  - Requerir `.venv` cuando se instale o ejecute algo (`uv venv .venv`; activar antes de correr comandos).
  - Instalar con `uv pip install -r requirements.txt`.
  - En proyectos dentro de `Eris`, usar un único `.venv` compartido en la carpeta raíz de `Eris` para todos los subproyectos. No crear `.venv` por subcarpeta; instalar dependencias de cada proyecto en ese mismo entorno.
- Estructura típica por competición:
  - `dataset/public/`, `working/`, `working/submission.csv`, `solution.py` (o notebook permitido), `README.md`.
- Entrega obligatoria por competición:
  - `solution.py` y `submission.csv`.
  - Actualizar en README: `## Time Spent` (horas estimadas), y `## Describe your approach` en inglés.

## Sección específica legado de AWS/operación (`VIEJO_REPO`)
- Mantener siempre presente en README local las instrucciones de seguridad y operación de AWS indicadas aquí.
