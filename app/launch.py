#!/usr/bin/env python3
"""
Launcher for Produktoprettelse-v2 Streamlit App

Usage:
  python app/launch.py
  
Or directly:
  streamlit run app/app.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit app."""
    app_path = Path(__file__).resolve().parent / "app.py"
    
    print("🚀 Launching Produktoprettelse-v2 UI...")
    print(f"📍 App: {app_path}")
    print("\n💻 Opening at: http://localhost:8501")
    print("📌 Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            check=False
        )
    except KeyboardInterrupt:
        print("\n\n✓ App stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
