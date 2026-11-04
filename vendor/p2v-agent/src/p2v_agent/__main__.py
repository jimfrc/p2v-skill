"""Allow ``python -m p2v_agent``."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
