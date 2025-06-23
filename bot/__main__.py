#!/usr/bin/env python3
"""Entry point for python -m bot execution."""

import asyncio
from .main import main

if __name__ == "__main__":
    asyncio.run(main())
