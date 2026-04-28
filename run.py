"""
Launcher — starts Streamlit in headless mode and opens the app in Google Chrome.

Run this from PyCharm instead of `streamlit run app.py` when you want the UI to
open in Chrome regardless of the system default browser.

The Streamlit server keeps running until you stop the run configuration
(red square in PyCharm) or press Ctrl+C.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

URL = "http://localhost:8501"

# Common Chrome install locations on Windows
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
]


def find_chrome() -> str | None:
    # Environment override first
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def main() -> int:
    project_dir = Path(__file__).resolve().parent
    os.chdir(project_dir)

    # Launch Streamlit headless (so it does NOT auto-open the default browser)
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    print("Starting Streamlit:", " ".join(cmd))
    server = subprocess.Popen(cmd)

    # Give the server a moment to bind the port
    time.sleep(3)

    chrome = find_chrome()
    if chrome:
        print(f"Opening in Chrome: {chrome}")
        subprocess.Popen([chrome, "--new-window", URL])
    else:
        print("Chrome not found. Set CHROME_PATH env var or install Chrome.")
        print("Falling back to default browser.")
        webbrowser.open(URL)

    # Wait for the Streamlit server to finish (user presses Stop / Ctrl+C)
    try:
        return server.wait()
    except KeyboardInterrupt:
        server.terminate()
        return 0


if __name__ == "__main__":
    sys.exit(main())
