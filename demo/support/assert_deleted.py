import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text())
if state["videos"]:
    raise SystemExit("The demo upload still exists")
print("Upload cleanup verified")
