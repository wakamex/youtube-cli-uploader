"""Cap idle gaps in an asciicast v3 recording without changing its output."""

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cast", type=Path)
    parser.add_argument("--max-idle", type=float, default=2.0)
    parser.add_argument("--final-pause", type=float, default=5.0)
    args = parser.parse_args()

    lines = args.cast.read_text().splitlines()
    shortened = 0
    output = [lines[0]]
    for line in lines[1:]:
        event = json.loads(line)
        if event[1] == "x":
            event[0] = args.final_pause
        elif event[0] > args.max_idle:
            event[0] = args.max_idle
            shortened += 1
        output.append(json.dumps(event, separators=(",", ":")))

    temporary = args.cast.with_suffix(args.cast.suffix + ".temporary")
    temporary.write_text("\n".join(output) + "\n")
    os.replace(temporary, args.cast)
    print(f"Shortened {shortened} idle gaps to {args.max_idle:g} seconds")
    print(f"Set the final pause to {args.final_pause:g} seconds")


if __name__ == "__main__":
    main()
