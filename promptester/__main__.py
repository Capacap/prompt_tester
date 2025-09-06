"""
Entry point for running the prompt tester as a module.

This enables execution via: python -m src
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
