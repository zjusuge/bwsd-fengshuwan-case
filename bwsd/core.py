"""No-critical-event BWSD implementation (manuscript Eqs. 3, 5, 6, 9-14).

Pre-formal ratios use the retrospectively fixed initialization bound and are
diagnostic only. Formal evaluation uses strictly prior evidence.
"""

from datetime import datetime
import numpy as np
import pandas as pd
from .parameters import *
from .validation import validate_daily_hydrology, parse_boolean


def finite_values(values) -> np.ndarray:
    """Return finite numeric values from an array-like object."""
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def safe_quantile(values, q: float) -> float:
    """Return quantile from finite values, or NaN if no finite value exists."""
    vals = finite_values(values)
    if vals.size == 0:
        return np.nan
    return float(np.quantile(vals, q))


def safe_max(values) -> float:
    """Return maximum from finite values, or NaN if no finite value exists."""
    vals = finite_values(values)
    if vals.size == 0:
        return np.nan
    return float(np.max(vals))


def warning_level(bwsd: float, theta_1: float, theta_2: float) -> float:
    """
    Convert BWSD into a management-oriented hydrological level.

    Levels
    ------
    0: normal hydrological state
    1: enhanced storage state
    2: high-storage sensitive state
    3: critical-reference hydrological state
    """
    if not np.isfinite(bwsd):
        return np.nan

    if bwsd < theta_1:
        return 0

    if bwsd < theta_2:
        return 1

    if bwsd < 1.0:
        return 2

    return 3


def evaluation_phase(date: pd.Timestamp, params: BWSDParameters) -> str:
    """Assign the evaluation phase for a given date."""
    if date < params.t0:
        return "Pre_reference"

    if date < params.raw_diagnostic_start:
        return "Hydrological_initialization"

    if date < params.formal_start:
        return "Threshold_initialization"

    return "Formal"


def max_value_and_date(df: pd.DataFrame, value_column: str) -> tuple[float, str]:
    """Return the maximum value and corresponding date string for a column."""
    if value_column not in df.columns:
        return np.nan, ""

    s = pd.to_numeric(df[value_column], errors="coerce")

    if not s.notna().any():
        return np.nan, ""

    idx = int(s.idxmax())
    value = float(s.loc[idx])
    date_string = pd.Timestamp(df.loc[idx, "Date"]).strftime("%Y-%m-%d")

    return value, date_string


def calculate_bwsd(
    hydrology: pd.DataFrame,
    params: BWSDParameters,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Calculate daily BWSD using a strictly forward-looking threshold rule.

    Parameters
    ----------
    hydrology : pandas.DataFrame
        Processed daily hydrological data.
    params : BWSDParameters
        Fixed BWSD parameter set.

    Returns
    -------
    tuple
        daily_bwsd, exceedance_table, metadata_table
    """
    hydrology = validate_daily_hydrology(hydrology)
    df = pd.DataFrame()

    df["Date"] = hydrology["Date"]
    df["Evaluation_phase"] = df["Date"].apply(lambda d: evaluation_phase(d, params))
    df["Is_formal"] = df["Date"] >= params.formal_start

    # Processed hydrological inputs.
    df["Precipitation_mm"] = hydrology["Precipitation_mm"]
    df["Evapotranspiration_mm"] = hydrology["Evapotranspiration_mm"]
    df["Water_level_m"] = hydrology["Water_level_m"]
    df["Runoff_mm"] = hydrology["Runoff_mm"]

    # Short aliases used in water-balance calculation.
    df["P_mm"] = df["Precipitation_mm"]
    df["E_mm"] = df["Evapotranspiration_mm"]
    df["Q_mm"] = df["Runoff_mm"]

    df["Flux_complete"] = df["P_mm"].notna() & df["E_mm"].notna() & df["Q_mm"].notna()

    # No debris-flow event was documented in this monitoring record.
    # No abnormal samples are released in the simplified public dataset.
    df["Debris_flow_event"] = parse_boolean(
        hydrology.get("Debris_flow_event", False), len(df)
    )
    if df["Debris_flow_event"].any():
        raise NotImplementedError(
            "This release implements the manuscript no-critical-event branch. Event-evidence mixing requires separately validated event records."
        )
    df["Abnormal_sample"] = parse_boolean(
        hydrology.get("Abnormal_sample", False), len(df)
    )
    if (
        "Noncritical_confirmed" not in hydrology
        and not params.assume_confirmed_noncritical
    ):
        raise ValueError(
            "Supply independently verified Noncritical_confirmed values for a new catchment"
        )
    confirmed = parse_boolean(
        hydrology.get("Noncritical_confirmed", params.assume_confirmed_noncritical),
        len(df),
    )
    confirmed_on = pd.to_datetime(
        hydrology.get("Confirmed_on", df["Date"]), errors="raise"
    ).to_numpy()
    if pd.isna(confirmed_on).any():
        raise ValueError("Confirmed_on must contain valid confirmation dates")
    if (confirmed_on < df["Date"].to_numpy()).any():
        raise ValueError("A response cannot be confirmed before its observation date")
    df["Noncritical_confirmed"] = confirmed
    df["Confirmed_on"] = pd.to_datetime(confirmed_on)

    df["Valid_for_threshold"] = (
        df["Flux_complete"] & (~df["Debris_flow_event"]) & (~df["Abnormal_sample"])
    )

    # In the present no-event case, prior complete and valid samples are treated
    # as non-event samples after they have occurred. The forward-looking rule is
    # enforced below by using only prior samples j < t.
    df["Non_event_threshold_sample"] = False

    # Apparent net water input.
    df["I_star_mm"] = np.where(
        df["Flux_complete"],
        df["P_mm"] - df["Q_mm"] - df["E_mm"],
        np.nan,
    )

    # -------------------------------------------------------------------------
    # 4.1 Apparent basin storage increment
    # -------------------------------------------------------------------------
    dates = df["Date"]

    if not dates.eq(params.t0).any():
        raise ValueError(
            f"T0 was not found in the input date sequence: {params.t0.date()}"
        )

    t0_idx = int(df.index[dates.eq(params.t0)][0])
    n = len(df)

    delta_s = np.full(n, np.nan, dtype=float)

    for i in range(n):
        if i < t0_idx:
            delta_s[i] = np.nan
            continue

        if i == t0_idx:
            delta_s[i] = 0.0
            continue

        previous_delta_s = delta_s[i - 1]

        if not np.isfinite(previous_delta_s):
            # Unknown storage does not silently restart at zero after a missing flux.
            delta_s[i] = np.nan
            continue

        i_star = df.loc[i, "I_star_mm"]

        if np.isfinite(i_star):
            delta_s[i] = max(0.0, previous_delta_s + float(i_star))
        else:
            policy = params.missing_flux_policy.lower()

            if policy == "carry":
                delta_s[i] = previous_delta_s
            elif policy == "nan":
                delta_s[i] = np.nan
            else:
                raise ValueError(
                    "Unsupported missing_flux_policy. Use 'carry' or 'nan'."
                )

    df["DeltaS_mm"] = delta_s

    # -------------------------------------------------------------------------
    # 4.2 Initialization lower bound
    # -------------------------------------------------------------------------
    init_mask = (
        (df["Date"] >= params.t0)
        & (df["Date"] < params.formal_start)
        & df["Valid_for_threshold"]
        & df["DeltaS_mm"].notna()
    )

    if not init_mask.any():
        raise ValueError("No valid initialization samples were found.")

    initialization_sample_days = int(init_mask.sum())
    initialization_max_delta_s = float(df.loc[init_mask, "DeltaS_mm"].max())
    s_init = max(params.s_min_mm, params.m0 * initialization_max_delta_s)

    # -------------------------------------------------------------------------
    # 4.3 Forward-looking critical-reference threshold
    # -------------------------------------------------------------------------
    s_stat_minus = np.full(n, np.nan, dtype=float)
    s_nc_minus = np.full(n, np.nan, dtype=float)
    s_crit_minus = np.full(n, np.nan, dtype=float)
    threshold_control = []
    eligible_noncritical = np.zeros(n, dtype=bool)
    frozen_bwsd = np.full(n, np.nan)

    index_array = np.arange(n)
    valid_array = df["Valid_for_threshold"].to_numpy(dtype=bool)
    non_event_array = eligible_noncritical
    delta_array = df["DeltaS_mm"].to_numpy(dtype=float)

    for i in range(n):
        # Strictly prior information only: j < i.
        prior_mask = (index_array < i) & valid_array & np.isfinite(delta_array)

        prior_values = delta_array[prior_mask]

        if finite_values(prior_values).size >= params.min_prior_for_stat:
            s_stat_minus[i] = safe_quantile(prior_values, params.p_stat)

        prior_non_event_mask = (
            prior_mask
            & non_event_array
            & (confirmed_on < dates.iloc[i].to_datetime64())
        )
        if params.episode_start:
            in_episode = (dates >= pd.Timestamp(params.episode_start)) & (
                dates <= pd.Timestamp(params.episode_end)
            )
            if dates.iloc[i] <= pd.Timestamp(params.episode_end):
                prior_non_event_mask &= ~in_episode.to_numpy()
                prior_mask &= ~in_episode.to_numpy()
                prior_values = delta_array[prior_mask]
                s_stat_minus[i] = (
                    safe_quantile(prior_values, params.p_stat)
                    if len(prior_values) >= params.min_prior_for_stat
                    else np.nan
                )
        prior_non_event_values = delta_array[prior_non_event_mask]

        if finite_values(prior_non_event_values).size >= params.min_prior_for_nc:
            s_nc_minus[i] = params.m_nc * safe_max(prior_non_event_values)

        components = {
            "S_min": params.s_min_mm,
            "S_init": s_init,
        }

        if np.isfinite(s_stat_minus[i]):
            components["S_stat"] = s_stat_minus[i]

        if np.isfinite(s_nc_minus[i]):
            components["S_nc"] = s_nc_minus[i]

        controlling_component = max(components, key=components.get)
        s_crit_minus[i] = float(components[controlling_component])
        threshold_control.append(controlling_component)
        if np.isfinite(delta_array[i]):
            frozen_bwsd[i] = delta_array[i] / s_crit_minus[i]
            eligible_noncritical[i] = (
                valid_array[i] and confirmed[i] and frozen_bwsd[i] >= params.theta_1
            )

    df["Non_event_threshold_sample"] = eligible_noncritical
    df["Preformal_retrospective_diagnostic"] = df["Date"] < params.formal_start
    df["S_stat_minus_mm"] = s_stat_minus
    df["S_nc_minus_mm"] = s_nc_minus
    df["S_init_mm"] = s_init
    df["S_crit_minus_mm"] = s_crit_minus
    df["Threshold_control"] = threshold_control

    # -------------------------------------------------------------------------
    # 4.4 BWSD and warning levels
    # -------------------------------------------------------------------------
    df["BWSD_all"] = df["DeltaS_mm"] / df["S_crit_minus_mm"]

    # Formal BWSD is retained only after the formal evaluation start.
    df["BWSD_formal"] = np.where(
        df["Date"] >= params.formal_start,
        df["BWSD_all"],
        np.nan,
    )

    df["BWSD_plot"] = df["BWSD_all"].clip(lower=0.0, upper=1.20)
    df["BWSD_0_1"] = df["BWSD_all"].clip(lower=0.0, upper=1.00)

    df["BWSD_level_all"] = df["BWSD_all"].apply(
        lambda x: warning_level(x, params.theta_1, params.theta_2)
    )

    df["BWSD_level_formal"] = df["BWSD_formal"].apply(
        lambda x: warning_level(x, params.theta_1, params.theta_2)
    )

    df["Theta_1"] = params.theta_1
    df["Theta_2"] = params.theta_2
    df["Critical_reference_level"] = 1.0

    # -------------------------------------------------------------------------
    # 4.5 Exceedance table
    # -------------------------------------------------------------------------
    exceedance_table = build_exceedance_table(df)

    # -------------------------------------------------------------------------
    # 4.6 Metadata
    # -------------------------------------------------------------------------
    metadata_table = build_metadata_table(
        df=df,
        params=params,
        initialization_sample_days=initialization_sample_days,
        initialization_max_delta_s=initialization_max_delta_s,
        s_init=s_init,
    )

    return df, exceedance_table, metadata_table


def build_exceedance_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build exceedance statistics for selected BWSD levels."""
    thresholds = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 1.00]

    rows = []

    formal_total_days = int(df["BWSD_formal"].notna().sum())

    for threshold in thresholds:
        all_days = int((df["BWSD_all"] >= threshold).sum())
        formal_days = int((df["BWSD_formal"] >= threshold).sum())

        if formal_total_days > 0:
            formal_percent = 100.0 * formal_days / formal_total_days
        else:
            formal_percent = np.nan

        rows.append(
            {
                "Threshold": threshold,
                "All_period_exceedance_days": all_days,
                "Formal_exceedance_days": formal_days,
                "Formal_total_days": formal_total_days,
                "Formal_exceedance_percent": round(formal_percent, 3),
            }
        )

    return pd.DataFrame(rows)


def build_metadata_table(
    df: pd.DataFrame,
    params: BWSDParameters,
    initialization_sample_days: int,
    initialization_max_delta_s: float,
    s_init: float,
) -> pd.DataFrame:
    """Build metadata and key result summary table."""
    cumulative_p = float(df["P_mm"].sum(skipna=True))
    cumulative_e = float(df["E_mm"].sum(skipna=True))
    cumulative_q = float(df["Q_mm"].sum(skipna=True))
    apparent_residual = cumulative_p - cumulative_e - cumulative_q

    max_delta_s, date_max_delta_s = max_value_and_date(df, "DeltaS_mm")
    max_bwsd_all, date_max_bwsd_all = max_value_and_date(df, "BWSD_all")
    max_bwsd_formal, date_max_bwsd_formal = max_value_and_date(df, "BWSD_formal")

    formal_days = int((df["Date"] >= params.formal_start).sum())
    formal_valid_days = int(df["BWSD_formal"].notna().sum())

    formal_ge_070 = int((df["BWSD_formal"] >= 0.70).sum())
    formal_ge_080 = int((df["BWSD_formal"] >= 0.80).sum())
    formal_ge_085 = int((df["BWSD_formal"] >= 0.85).sum())
    formal_ge_090 = int((df["BWSD_formal"] >= 0.90).sum())
    formal_ge_095 = int((df["BWSD_formal"] >= 0.95).sum())
    formal_ge_100 = int((df["BWSD_formal"] >= 1.00).sum())

    rows = [
        ("Script", SCRIPT_NAME),
        ("Generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Catchment_name", params.catchment_name),
        ("Catchment_area_km2", params.catchment_area_km2),
        ("Input_dataset_title", params.dataset_title),
        ("Input_dataset_version", params.dataset_version),
        ("Input_dataset_DOI", params.dataset_doi),
        ("Input_dataset_URL", params.dataset_url),
        ("Input_dataset_citation", params.dataset_citation),
        ("Date_range", f"{df['Date'].min().date()} to {df['Date'].max().date()}"),
        ("Total_days", int(len(df))),
        ("T0", params.t0.strftime("%Y-%m-%d")),
        ("Raw_diagnostic_start", params.raw_diagnostic_start.strftime("%Y-%m-%d")),
        ("Formal_evaluation_start", params.formal_start.strftime("%Y-%m-%d")),
        ("Hydrological_initialization_days", params.hydrological_initialization_days),
        ("Formal_initialization_days", params.formal_initialization_days),
        ("Initialization_sample_days", initialization_sample_days),
        ("P_STAT", params.p_stat),
        ("M0", params.m0),
        ("M_NC", params.m_nc),
        ("S_MIN_mm", params.s_min_mm),
        ("Theta_1", params.theta_1),
        ("Theta_2", params.theta_2),
        ("Minimum_prior_samples_for_stat", params.min_prior_for_stat),
        ("Minimum_prior_samples_for_non_event", params.min_prior_for_nc),
        ("Missing_flux_policy", params.missing_flux_policy),
        ("Cumulative_precipitation_mm", round(cumulative_p, 6)),
        ("Cumulative_evapotranspiration_mm", round(cumulative_e, 6)),
        ("Cumulative_runoff_mm", round(cumulative_q, 6)),
        ("Apparent_water_balance_residual_mm", round(apparent_residual, 6)),
        ("Initialization_max_DeltaS_mm", round(initialization_max_delta_s, 6)),
        ("S_init_mm", round(s_init, 6)),
        ("Max_DeltaS_mm", round(max_delta_s, 6)),
        ("Date_of_max_DeltaS", date_max_delta_s),
        ("Max_BWSD_all", round(max_bwsd_all, 6)),
        ("Date_of_max_BWSD_all", date_max_bwsd_all),
        ("Max_BWSD_formal", round(max_bwsd_formal, 6)),
        ("Date_of_max_BWSD_formal", date_max_bwsd_formal),
        ("Formal_days", formal_days),
        ("Formal_valid_BWSD_days", formal_valid_days),
        ("Formal_BWSD_ge_0.70_days", formal_ge_070),
        ("Formal_BWSD_ge_0.80_days", formal_ge_080),
        ("Formal_BWSD_ge_0.85_days", formal_ge_085),
        ("Formal_BWSD_ge_0.90_days", formal_ge_090),
        ("Formal_BWSD_ge_0.95_days", formal_ge_095),
        ("Formal_BWSD_ge_1.00_days", formal_ge_100),
        ("Documented_debris_flow_events", 0),
        (
            "Forward_looking_rule",
            "Formal thresholds use only prior confirmed evidence; pre-formal ratios use the retrospective initialization bound and are diagnostic only.",
        ),
        (
            "Code_scope",
            "This script performs the core BWSD calculation and summary export.",
        ),
    ]

    return pd.DataFrame(rows, columns=["Item", "Value"])
