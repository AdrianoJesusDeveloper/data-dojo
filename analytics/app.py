"""Compatibility entrypoint for Streamlit Cloud.

The canonical dashboard lives in streamlit_app.py. Keeping this tiny wrapper
prevents older deployments configured with analytics/app.py from serving the
obsolete placeholder dashboard.
"""

from pathlib import Path

exec((Path(__file__).resolve().parent / "streamlit_app.py").read_text(encoding="utf-8"))
