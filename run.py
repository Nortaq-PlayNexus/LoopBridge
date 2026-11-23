#!/usr/bin/env python3
"""Convenience launcher for LoopBridge.

    python run.py --simulate --count 2     # rehearse the loop anywhere
    python run.py                          # real run on Windows 11
    python run.py --gui                    # desktop UI on Windows 11
"""

from loopbridge.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
