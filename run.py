#!/usr/bin/env python3
"""
ExpenseIQ - Single-Terminal Launcher
Starts Flask backend (port 5000) and Streamlit frontend (port 8501) together.
Press Ctrl+C to stop both services.
"""

import subprocess
import sys
import os
import time
import signal
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))

BANNER = """
╔════════════════════════════════════════════════╗
║          💳  ExpenseIQ  —  Starting Up         ║
║  Personal Expense Management with AI Chat      ║
╚════════════════════════════════════════════════╝
"""

processes = []

def stream_output(proc, prefix, color_code):
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            print(f"\033[{color_code}m[{prefix}]\033[0m {text}", flush=True)

def shutdown(sig=None, frame=None):
    print("\n\n⏹  Shutting down ExpenseIQ...")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    time.sleep(1)
    for p in processes:
        try:
            p.kill()
        except:
            pass
    print("✅ All services stopped. Goodbye!")
    sys.exit(0)

signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)

def main():
    print(BANNER)

    try:
        import flask, streamlit, requests, pandas
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Run:  pip install flask streamlit requests pandas")
        sys.exit(1)

    print("🚀 Starting Flask backend  →  http://localhost:5000")
    flask_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1
    )
    processes.append(flask_proc)

    time.sleep(2)
    if flask_proc.poll() is not None:
        out, _ = flask_proc.communicate()
        print("❌ Flask failed to start:")
        print(out.decode("utf-8", errors="replace"))
        shutdown()

    print("🌐 Starting Streamlit frontend  →  http://localhost:8501")
    st_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend.py",
         "--server.port", "8501",
         "--server.address", "localhost",
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1
    )
    processes.append(st_proc)

    threading.Thread(target=stream_output, args=(flask_proc, "FLASK",     "32"), daemon=True).start()
    threading.Thread(target=stream_output, args=(st_proc,    "STREAMLIT", "34"), daemon=True).start()

    time.sleep(3)
    print("""
┌─────────────────────────────────────────────────┐
│  ✅ ExpenseIQ is running!                        │
│                                                  │
│  🌐 Open in browser:  http://localhost:8501      │
│  🔧 Flask API:        http://localhost:5000/api  │
│                                                  │
│  🤖 AI Chat requires Ollama running locally:     │
│     ollama serve  (in a separate terminal)       │
│     ollama pull gemma3:1b                        │
│                                                  │
│  Press  Ctrl+C  to stop all services             │
└─────────────────────────────────────────────────┘
""")

    while True:
        time.sleep(5)
        if flask_proc.poll() is not None:
            print("⚠️  Flask crashed. Restarting...")
            flask_proc = subprocess.Popen(
                [sys.executable, "app.py"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            processes[0] = flask_proc
            threading.Thread(target=stream_output, args=(flask_proc, "FLASK", "32"), daemon=True).start()

if __name__ == "__main__":
    main()
