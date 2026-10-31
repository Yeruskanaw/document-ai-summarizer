import subprocess
import sys

packages = ["google-genai", "pypdf", "python-dotenv", "streamlit"]
subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
print("ההתקנה הסתיימה בהצלחה!")
