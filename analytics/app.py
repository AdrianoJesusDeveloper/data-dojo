"""Entrypoint compatível com Streamlit Cloud."""
from pathlib import Path

exec((Path(__file__).resolve().parent / "streamlit_app.py").read_text(encoding="utf-8"))
