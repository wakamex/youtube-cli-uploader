import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists() or not json.loads(path.read_text()).get("videos"):
    raise SystemExit(1)
