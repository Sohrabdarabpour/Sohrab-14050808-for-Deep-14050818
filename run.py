"""اجرای برنامه.

پیش‌فرض امن است: فقط روی 127.0.0.1 و بدون debug.
برای توسعه:

    $env:FLASK_DEBUG = "1"        # ویندوز (PowerShell)
    python run.py

برای دسترسی از شبکه (فقط وقتی لازم است):

    $env:SSPE_HOST = "0.0.0.0"
"""

import os

from app import create_app
from config import Config

app = create_app()

if __name__ == "__main__":
    if Config.DEBUG and os.environ.get("SSPE_HOST", "127.0.0.1") == "0.0.0.0":
        print(
            "WARNING: debug mode is exposed on 0.0.0.0 — "
            "the Werkzeug debugger can allow arbitrary code execution."
        )

    app.run(
        debug=Config.DEBUG,
        host=os.environ.get("SSPE_HOST", "127.0.0.1"),
        port=int(os.environ.get("SSPE_PORT", "5000")),
    )
