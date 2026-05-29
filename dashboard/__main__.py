"""Entry point for ``python -m dashboard`` — launches Streamlit dashboard."""

import os
import sys
from streamlit.web import cli as stcli

if __name__ == "__main__":
    entry = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "dashboard.py"))
    sys.argv = ["streamlit", "run", entry, "--server.port=8501"]
    stcli.main()
