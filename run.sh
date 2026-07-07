#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# One-command bootstrap + serve for the Cocktail app (macOS / Linux).
#
#   bash run.sh
#
# - Creates an isolated virtualenv at ./venv (your system Python is untouched)
# - Installs requirements.txt (only when needed)
# - Copies .env.example → .env on first run
# - Launches uvicorn on HOST:PORT (defaults 0.0.0.0:8000), reachable on the LAN
#
# To stop the server: Ctrl-C
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
VENV="venv"

# --- virtual environment --------------------------------------------------
if [ ! -d "$VENV" ]; then
  echo "▶ Creating virtual environment at ./$VENV ..."
  "$PY" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# --- dependencies ---------------------------------------------------------
echo "▶ Ensuring dependencies are installed ..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

# --- .env -----------------------------------------------------------------
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "▶ Created .env from .env.example — edit it to set LLM_API_KEY, then re-run."
  fi
fi

# load HOST/PORT from .env if present (defaults: 0.0.0.0 / 8000)
HOST="0.0.0.0"
PORT="8000"
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1090
  . ./.env
  set +a
fi
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# --- launch ---------------------------------------------------------------
echo "▶ Starting uvicorn on ${HOST}:${PORT} ..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
