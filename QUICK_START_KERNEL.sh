#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
REQ_FILE="$PROJECT_DIR/requirements.txt"
LIB_DIR="$PROJECT_DIR/lib"
ENV_EXAMPLE_ROOT="$PROJECT_DIR/.env.example"
ENV_EXAMPLE_LIB="$LIB_DIR/.env.example"
ENV_FILE="$LIB_DIR/.env"

mkdir -p "$LIB_DIR"
python3 -m pip install --target "$LIB_DIR" -r "$REQ_FILE"

if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE_ROOT" ]; then
  cp "$ENV_EXAMPLE_ROOT" "$ENV_FILE"
elif [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE_LIB" ]; then
  cp "$ENV_EXAMPLE_LIB" "$ENV_FILE"
fi

KERNEL_DIR="$HOME/.local/share/jupyter/kernels/rauda-ai-llm"
PYTHON_BIN="$(command -v python3)"
RUNTIME_PYTHONPATH="$LIB_DIR"
if [ -n "${PYTHONPATH:-}" ]; then
  RUNTIME_PYTHONPATH="$LIB_DIR:$PYTHONPATH"
fi

mkdir -p "$KERNEL_DIR"
cat > "$KERNEL_DIR/kernel.json" <<EOF
{
  "argv": [
    "$PYTHON_BIN",
    "-m",
    "ipykernel_launcher",
    "-f",
    "{connection_file}"
  ],
  "display_name": "Python (Rauda AI)",
  "language": "python",
  "env": {
    "PYTHONPATH": "$RUNTIME_PYTHONPATH"
  }
}
EOF

echo "Listo. En Jupyter selecciona el kernel: Python (Rauda AI)"
