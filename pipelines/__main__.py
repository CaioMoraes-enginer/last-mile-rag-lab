"""Permite rodar `python -m pipelines` como atalho do pipeline P1 (KAN-7)."""
from pipelines.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
