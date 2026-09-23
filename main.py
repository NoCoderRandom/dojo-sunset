#!/usr/bin/env python3
"""Start Dojo Sunset from this directory or any desktop launcher."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from dojo.app import main

if __name__ == '__main__':
    main()
