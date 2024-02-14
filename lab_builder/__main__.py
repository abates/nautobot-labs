#!/usr/bin/env python3
"""This is the main entrypoint for running `lab_builder` labs."""
import sys

from .runner import LabRunner

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path to lab>", file=sys.stderr)
        sys.exit(1)

    LabRunner(sys.argv[1]).cmdloop()
