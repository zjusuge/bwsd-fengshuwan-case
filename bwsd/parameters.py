"""Fixed case configuration and validated parameter contracts."""

from dataclasses import dataclass
import math
import pandas as pd

SCRIPT_NAME = "bwsd"

DATASET_TITLE = (
    "Processed Daily Hydrological Dataset for the Fengshuwan Catchment, "
    "Zhejiang, China, 2023–2026"
)

DATASET_VERSION = "v1.0.0"
DATASET_DOI = "10.5281/zenodo.20068173"
DATASET_URL = "https://doi.org/10.5281/zenodo.20068173"

DATASET_CITATION = (
    "Wang, T. (2026). Processed Daily Hydrological Dataset for the "
    "Fengshuwan Catchment, Zhejiang, China, 2023–2026 "
    "(v1.0.0) [Data set]. Zenodo. "
    "https://doi.org/10.5281/zenodo.20068173"
)


# =============================================================================
# 1. Parameters
# =============================================================================


@dataclass(frozen=True)
class BWSDParameters:
    """Fixed parameter set for the Fengshuwan daily BWSD case calculation."""

    catchment_name: str = "Fengshuwan catchment"
    catchment_area_km2: float = 0.8461

    # Archived input dataset information.
    dataset_title: str = DATASET_TITLE
    dataset_version: str = DATASET_VERSION
    dataset_doi: str = DATASET_DOI
    dataset_url: str = DATASET_URL
    dataset_citation: str = DATASET_CITATION

    # Low-storage reference date.
    t0: pd.Timestamp = pd.Timestamp("2023-10-12")

    # Initialization settings.
    hydrological_initialization_days: int = 90
    formal_initialization_days: int = 365

    # Threshold-construction parameters.
    p_stat: float = 0.98
    m0: float = 1.20
    m_nc: float = 1.20
    s_min_mm: float = 20.0

    # Management-oriented BWSD levels.
    theta_1: float = 0.70
    theta_2: float = 0.90

    # Minimum prior samples for threshold components.
    min_prior_for_stat: int = 30
    # S1 activates the field constraint after a qualified confirmed response.
    min_prior_for_nc: int = 1

    # Missing-flux policy.
    # "carry": keep previous DeltaS if P, E, or Q is missing.
    # "nan": set DeltaS to NaN on missing-flux days.
    missing_flux_policy: str = "carry"
    # These defaults replay the independently monitored, non-critical case.
    assume_confirmed_noncritical: bool = True
    episode_start: str | None = None
    episode_end: str | None = None

    def __post_init__(self):
        for name in [
            "catchment_area_km2",
            "p_stat",
            "m0",
            "m_nc",
            "s_min_mm",
            "theta_1",
            "theta_2",
        ]:
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.catchment_area_km2 <= 0:
            raise ValueError("Catchment area must be positive")
        for name in [
            "hydrological_initialization_days",
            "formal_initialization_days",
            "min_prior_for_stat",
            "min_prior_for_nc",
        ]:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        reference = pd.Timestamp(self.t0)
        if (
            pd.isna(reference)
            or reference.tz is not None
            or reference != reference.normalize()
        ):
            raise ValueError("t0 must be a valid timezone-naive calendar date")
        object.__setattr__(self, "t0", reference)
        if not isinstance(self.assume_confirmed_noncritical, bool):
            raise ValueError("assume_confirmed_noncritical must be Boolean")
        if not 0 < self.p_stat < 1:
            raise ValueError("p_stat must lie strictly between 0 and 1")
        if self.m0 < 1 or self.m_nc < 1 or self.s_min_mm <= 0:
            raise ValueError("Safety coefficients must be >= 1 and s_min_mm positive")
        if not 0 < self.theta_1 < self.theta_2 < 1:
            raise ValueError("Require 0 < theta_1 < theta_2 < 1")
        if self.formal_initialization_days <= self.hydrological_initialization_days:
            raise ValueError(
                "Formal initialization must exceed hydrological initialization"
            )
        if self.min_prior_for_stat < 1 or self.min_prior_for_nc < 1:
            raise ValueError("Minimum history sizes must be positive")
        if self.missing_flux_policy not in {"carry", "nan"}:
            raise ValueError("missing_flux_policy must be carry or nan")
        if bool(self.episode_start) != bool(self.episode_end):
            raise ValueError("An embargo needs both episode_start and episode_end")
        if self.episode_start:
            for bound in [self.episode_start, self.episode_end]:
                value = pd.Timestamp(bound)
                if pd.isna(value) or value.tz is not None or value != value.normalize():
                    raise ValueError(
                        "Episode bounds must be valid timezone-naive dates"
                    )
        if self.episode_start and pd.Timestamp(self.episode_start) > pd.Timestamp(
            self.episode_end
        ):
            raise ValueError("Episode start must not follow episode end")

    @property
    def raw_diagnostic_start(self) -> pd.Timestamp:
        """Start date after hydrological initialization."""
        return self.t0 + pd.Timedelta(days=self.hydrological_initialization_days)

    @property
    def formal_start(self) -> pd.Timestamp:
        """Start date of the formal forward-looking evaluation period."""
        return self.t0 + pd.Timedelta(days=self.formal_initialization_days)
