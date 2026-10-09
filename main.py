"""Backward-compatible command and import surface for the BWSD repository."""

from bwsd.parameters import *
from bwsd.core import *
from bwsd.io import *
from bwsd.cli import main

if __name__ == "__main__":
    main()
