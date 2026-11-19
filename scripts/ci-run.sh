#!/bin/sh
# Preserve command status and expose a bounded diagnostic in Actions annotations.
set -eu
log=$(mktemp)
trap 'rm -f -- "$log"' EXIT HUP INT TERM
if "$@" >"$log" 2>&1; then
    cat "$log"
else
    status=$?
    cat "$log"
    python3 - "$log" "$status" <<'PY'
from pathlib import Path
import sys

lines = Path(sys.argv[1]).read_text(errors='replace').splitlines()[-40:]
message = f'Command failed with exit status {sys.argv[2]}:\n' + '\n'.join(lines)
message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
print(f'::error::{message}')
PY
    exit "$status"
fi
