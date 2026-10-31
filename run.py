import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "streamlit", "run", "app.py"])