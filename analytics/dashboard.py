"""Deprecated compatibility entrypoint.

Use analytics/streamlit_app.py for the Dojo Command Center.
"""

from pathlib import Path

exec((Path(__file__).resolve().parent / "streamlit_app.py").read_text(encoding="utf-8"))
