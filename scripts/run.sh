#!/usr/bin/env sh
# Thin launcher for macOS/Linux (and Git Bash on Windows).
# All arguments are forwarded to p2v-agent.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Verify a candidate really is a working Python >= 3.10. This skips the
# Microsoft Store "python3" app-alias stub, which exits non-zero with no output.
is_usable_python() {
    "$1" ${2:-} -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && is_usable_python "$candidate"; then
        exec "$candidate" "$SCRIPT_DIR/p2v.py" "$@"
    fi
done

if command -v py >/dev/null 2>&1 && is_usable_python py -3; then
    exec py -3 "$SCRIPT_DIR/p2v.py" "$@"
fi

echo "p2v-agent-skill: Python 3.10+ is required (no working python3/python/py found)." >&2
exit 1
