"""Scientific regression and information-timing contracts."""

from dataclasses import replace
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from bwsd import BWSDParameters, load_daily_hydrology, calculate_bwsd
from bwsd.analysis import (
    comparator_indicators,
    persistence_diagnostics,
    replay_flux,
    monte_carlo,
)
from bwsd.validation import validate_daily_hydrology, parse_boolean

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def data():
    return load_daily_hydrology(
        ROOT / "data/fengshuwan_processed_daily_hydrology.xlsx", "Daily_Data"
    )


@pytest.fixture(scope="module")
def daily(data):
    return calculate_bwsd(data, BWSDParameters())[0]


def synthetic(n=20):
    return pd.DataFrame(
        {
            "Date": pd.date_range("2023-10-12", periods=n),
            "Precipitation_mm": [99.0] + [1.0] * (n - 1),
            "Evapotranspiration_mm": 0.0,
            "Water_level_m": 0.1,
            "Runoff_mm": 0.0,
        }
    )


def short_params(**kwargs):
    return BWSDParameters(
        hydrological_initialization_days=2,
        formal_initialization_days=4,
        s_min_mm=1.0,
        min_prior_for_nc=1,
        min_prior_for_stat=1,
        **kwargs
    )


def test_released_dataset_hash():
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    for item in manifest["files"]:
        assert (
            hashlib.sha256((ROOT / "data" / item["path"]).read_bytes()).hexdigest()
            == item["sha256"]
        )


def test_entire_formal_trajectory_matches_archived_workbook(daily):
    old = pd.read_excel(
        ROOT / "results/fengshuwan_bwsd_results.xlsx", sheet_name="Daily_BWSD"
    )
    mask = daily.Is_formal
    for name in ["DeltaS_mm", "S_crit_minus_mm", "BWSD_formal"]:
        np.testing.assert_allclose(
            daily.loc[mask, name], old.loc[mask, name], rtol=0, atol=1e-10
        )


def test_reported_case_values(daily):
    assert len(daily) == 908 and daily.Is_formal.sum() == 543
    assert daily.S_init_mm.iloc[0] == pytest.approx(479.2503622166597, abs=1e-6)
    assert daily.DeltaS_mm.max() == pytest.approx(473.112715, abs=1e-6)
    assert daily.loc[daily.DeltaS_mm.idxmax(), "Date"] == pd.Timestamp("2025-06-26")
    assert daily.BWSD_formal.max() == pytest.approx(0.935957, abs=1e-6)
    assert daily.loc[daily.BWSD_formal.idxmax(), "Date"] == pd.Timestamp("2025-06-22")
    assert [(daily.BWSD_formal >= t).sum() for t in [0.7, 0.8, 0.85, 0.9, 0.95, 1]] == [
        165,
        22,
        2,
        1,
        0,
        0,
    ]


def test_future_data_cannot_rewrite_formal_prefix(data, daily):
    cut = 600
    partial = calculate_bwsd(data.iloc[:cut].copy(), BWSDParameters())[0]
    altered = data.copy()
    altered.loc[cut:, "Precipitation_mm"] += 500
    changed = calculate_bwsd(altered, BWSDParameters())[0]
    for name in ["DeltaS_mm", "S_crit_minus_mm", "BWSD_formal"]:
        np.testing.assert_allclose(
            partial[name], daily[name].iloc[:cut], equal_nan=True
        )
        np.testing.assert_allclose(
            changed[name].iloc[:cut], daily[name].iloc[:cut], equal_nan=True
        )


def test_current_evidence_does_not_change_its_own_denominator(data, daily):
    changed = data.copy()
    changed.loc[600, "Precipitation_mm"] += 1000
    result = calculate_bwsd(changed, BWSDParameters())[0]
    assert result.S_crit_minus_mm.iloc[600] == daily.S_crit_minus_mm.iloc[600]
    assert result.BWSD_formal.iloc[600] > daily.BWSD_formal.iloc[600]


def test_initial_flux_is_not_accumulated_and_storage_is_nonnegative():
    data = synthetic()
    data.loc[5, "Runoff_mm"] = 100
    daily = calculate_bwsd(data, short_params())[0]
    assert daily.DeltaS_mm.iloc[0] == 0
    assert daily.DeltaS_mm.iloc[1] == 1
    assert daily.DeltaS_mm.iloc[5] == 0
    assert (daily.DeltaS_mm >= 0).all()


def test_confirmation_delay_defers_activation():
    data = synthetic()
    data["Noncritical_confirmed"] = True
    data["Confirmed_on"] = data.Date + pd.Timedelta(days=5)
    delayed = calculate_bwsd(data, short_params())[0]
    immediate = calculate_bwsd(data.drop(columns="Confirmed_on"), short_params())[0]
    assert immediate.S_nc_minus_mm.iloc[4] > 0
    assert pd.isna(delayed.S_nc_minus_mm.iloc[4])
    assert pd.isna(delayed.S_nc_minus_mm.iloc[8])
    assert delayed.S_nc_minus_mm.iloc[9] > 0


def test_embargo_keeps_episode_denominator_fixed(data):
    params = replace(
        BWSDParameters(), episode_start="2025-06-01", episode_end="2025-07-10"
    )
    daily = calculate_bwsd(data, params)[0]
    episode = daily.loc[daily.Date.between(params.episode_start, params.episode_end)]
    assert episode.S_crit_minus_mm.nunique() == 1
    assert episode.BWSD_all.max() == pytest.approx(0.987, abs=0.001)
    assert (
        daily.loc[daily.Date.eq("2025-07-11"), "S_crit_minus_mm"].iloc[0]
        > episode.S_crit_minus_mm.iloc[-1]
    )


def test_missing_flux_policies_do_not_reinitialize_storage():
    data = synthetic()
    data.loc[6, "Precipitation_mm"] = np.nan
    carry = calculate_bwsd(data, short_params())[0]
    unknown = calculate_bwsd(data, short_params(missing_flux_policy="nan"))[0]
    assert carry.DeltaS_mm.iloc[6] == carry.DeltaS_mm.iloc[5]
    assert carry.DeltaS_mm.iloc[7] == carry.DeltaS_mm.iloc[5] + 1
    assert not carry.Valid_for_threshold.iloc[6]
    assert unknown.DeltaS_mm.iloc[6:].isna().all()


def test_unsupported_event_evidence_is_rejected():
    data = synthetic()
    data["Debris_flow_event"] = False
    data.loc[10, "Debris_flow_event"] = True
    with pytest.raises(NotImplementedError):
        calculate_bwsd(data, short_params())


def test_new_catchment_needs_independent_confirmation():
    with pytest.raises(ValueError, match="independently"):
        calculate_bwsd(synthetic(), short_params(assume_confirmed_noncritical=False))


@pytest.mark.parametrize(
    "change",
    [
        {"p_stat": 1.0},
        {"m0": 0.9},
        {"theta_1": 0.95},
        {"s_min_mm": float("nan")},
        {"m_nc": float("inf")},
        {"catchment_area_km2": 0},
        {"formal_initialization_days": 1},
        {"min_prior_for_nc": 0},
        {"formal_initialization_days": 365.5},
        {"missing_flux_policy": "reset"},
        {"episode_start": "2025-06-01"},
        {"episode_start": "2025-07-10", "episode_end": "2025-06-01"},
        {"assume_confirmed_noncritical": "false"},
        {"t0": "NaT"},
    ],
)
def test_invalid_parameters_are_rejected(change):
    with pytest.raises((ValueError, TypeError)):
        BWSDParameters(**change)


@pytest.mark.parametrize(
    "kind", ["gap", "duplicate", "negative", "infinite", "text", "empty"]
)
def test_invalid_input_is_rejected(kind):
    data = synthetic()
    if kind == "gap":
        data = data.drop(index=4)
    if kind == "duplicate":
        data.loc[4, "Date"] = data.loc[3, "Date"]
    if kind == "negative":
        data.loc[4, "Runoff_mm"] = -1
    if kind == "infinite":
        data.loc[4, "Precipitation_mm"] = np.inf
    if kind == "text":
        data["Precipitation_mm"] = data.Precipitation_mm.astype(object)
        data.loc[4, "Precipitation_mm"] = "bad"
    if kind == "empty":
        data = data.iloc[:0]
    with pytest.raises(ValueError):
        validate_daily_hydrology(data)


@pytest.mark.parametrize("flag", ["yes", "unknown", None])
def test_ambiguous_evidence_flags_are_rejected(flag):
    with pytest.raises(ValueError):
        parse_boolean([flag], 1)


def test_loader_rejects_malformed_numeric_strings(tmp_path):
    data = synthetic()
    data["Runoff_mm"] = data.Runoff_mm.astype(object)
    data.loc[5, "Runoff_mm"] = "bad"
    path = tmp_path / "invalid.csv"
    data.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_daily_hydrology(path, "Daily_Data")


def test_comparator_and_persistence_values(daily):
    _, stats = comparator_indicators(daily)
    assert stats["Days_ge_0.70"].tolist() == [165, 17, 29, 22, 19, 543, 543]
    metrics, _ = persistence_diagnostics(daily, BWSDParameters().formal_start)
    # The manuscript reports NSE to three decimal places.
    np.testing.assert_allclose(metrics.NSE, [0.982, 0.943], atol=0.0005)
    np.testing.assert_allclose(metrics.F1, [0.975758, 0.963636], atol=1e-6)
    assert metrics.N.tolist() == [543, 543]


def test_comparator_values_on_reported_peak_date(daily):
    indicators, _ = comparator_indicators(daily)
    row = indicators.loc[indicators.Date.eq("2025-06-22")].iloc[0]
    for name, expected in [
        ("P3d", 1.205),
        ("P7d", 0.813),
        ("P15d", 1.076),
        ("API0.90", 1.039),
        ("P-E", 0.880),
        ("P-Q", 0.875),
    ]:
        assert row[name] == pytest.approx(expected, abs=0.0005)


def test_fast_qualified_kernel_matches_full_core(data, daily):
    flux = (
        data.Precipitation_mm - data.Runoff_mm - data.Evapotranspiration_mm
    ).to_numpy()
    np.testing.assert_allclose(
        replay_flux(flux, BWSDParameters()), daily.BWSD_formal, equal_nan=True
    )
    rng = np.random.default_rng(123)
    changed = data.copy()
    changed["Precipitation_mm"] *= rng.uniform(0.6, 1.4, len(data))
    expected = calculate_bwsd(changed, BWSDParameters())[0]
    flux = (
        changed.Precipitation_mm - changed.Runoff_mm - changed.Evapotranspiration_mm
    ).to_numpy()
    np.testing.assert_allclose(
        replay_flux(flux, BWSDParameters()), expected.BWSD_formal, equal_nan=True
    )


def test_paper_kernel_matches_independent_running_prior_max(data):
    from bwsd.analysis import storage_from_flux

    flux = (
        data.Precipitation_mm - data.Runoff_mm - data.Evapotranspiration_mm
    ).to_numpy()
    delta = storage_from_flux(flux)
    prior = np.r_[0, np.maximum.accumulate(delta)[:-1]]
    reference = np.maximum(1.2 * delta[:365].max(), 1.2 * prior)
    reference[:30] = 1.2 * delta[:365].max()
    expected = delta / reference
    expected[:365] = np.nan
    np.testing.assert_allclose(
        replay_flux(flux, BWSDParameters(), "paper-prior"), expected, equal_nan=True
    )


def test_monte_carlo_reproduces_reported_interval(data):
    quality = pd.read_csv(ROOT / "data/quality_flags.csv")
    _, _, summary = monte_carlo(data, quality, BWSDParameters())
    assert summary["maximum_bwsd_median"] == pytest.approx(0.931068, abs=1e-6)
    assert summary["maximum_bwsd_p05"] == pytest.approx(0.904406, abs=1e-6)
    assert summary["maximum_bwsd_p95"] == pytest.approx(0.949092, abs=1e-6)
    assert summary["realizations_with_critical_reference_exceedance"] == 0
    assert summary["threshold_policy"] == "paper-prior"


def test_quality_dates_and_confirmation_are_not_silently_ignored(data):
    quality = pd.read_csv(ROOT / "data/quality_flags.csv")
    with pytest.raises(ValueError, match="align"):
        monte_carlo(data, quality.iloc[:-1], BWSDParameters(), realizations=1)
    changed = data.copy()
    changed["Noncritical_confirmed"] = False
    with pytest.raises(ValueError, match="confirmed"):
        monte_carlo(changed, quality, BWSDParameters(), realizations=1)
