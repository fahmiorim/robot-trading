"""Allow ``python -m src`` to launch the dashboard."""

import os
import subprocess
import sys

dashboard = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "__init__.py"))
port = 8510
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    port = int(sys.argv[1])

cmd = [sys.executable, "-m", "streamlit", "run", dashboard, f"--server.port={port}"]
sys.exit(subprocess.call(cmd))
