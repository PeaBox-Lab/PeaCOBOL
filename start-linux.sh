#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

echo "PeaCOBOL 1.0.0 - Linux launcher"
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "ERROR: Python 3.10 or newer was not found." >&2
  exit 1
fi

"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' || {
  echo "ERROR: PeaCOBOL requires Python 3.10 or newer." >&2
  exit 1
}

echo "Starting the secure local GUI..."
echo "Keep this terminal open. Press Ctrl+C to stop PeaCOBOL."
exec "$PYTHON" -m peacobol.server --root "$SCRIPT_DIR" --port 8765 --open-browser
