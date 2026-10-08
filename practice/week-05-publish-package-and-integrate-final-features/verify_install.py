#!/usr/bin/env python3
"""Root runner for verifying package installation and functionality."""

import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from datapipeline.verify_install import main

if __name__ == "__main__":
    main()
