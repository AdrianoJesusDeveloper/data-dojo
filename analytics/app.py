"""Entrypoint oficial do Dojo Command Center no Streamlit Cloud."""
from pathlib import Path

exec((Path(__file__).resolve().parent / "streamlit_app.py").read_text(encoding="utf-8"))
