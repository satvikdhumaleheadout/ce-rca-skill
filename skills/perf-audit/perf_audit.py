#!/usr/bin/env python3
"""
Perf Audit v6.1 entry point.

Usage:
    python3 perf_audit.py render --ce-id 3593 --ce-name "Antelope Canyon" ...
    python3 perf_audit.py data ce-health --ce-id 3593 ...
"""

import os
import sys

_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from engine.cli import data_main, render_main

if __name__ == "__main__":
    os.environ["PERF_AUDIT_VERSION"] = "v6.2"
    if len(sys.argv) > 1 and sys.argv[1] == "render":
        render_main(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == "data":
        data_main(sys.argv[2:])
    else:
        print("Usage: python3 perf_audit.py [render|data] [options]")
        print("  render  — Fetch BQ data and render markdown skeleton")
        print("  data    — Fetch and display raw BQ data")
        sys.exit(1)
