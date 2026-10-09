"""BWSD case-study software."""

from .parameters import BWSDParameters
from .core import calculate_bwsd
from .io import load_daily_hydrology

__version__ = "1.1.0"
__all__ = ["BWSDParameters", "calculate_bwsd", "load_daily_hydrology"]
