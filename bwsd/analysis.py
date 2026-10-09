"""Post-sequence diagnostics; none of these analyses change frozen daily BWSD."""

from dataclasses import replace
import numpy as np
import pandas as pd
from .core import calculate_bwsd
from .parameters import BWSDParameters

SEED = 20260505


def storage_from_flux(flux):
    out = np.zeros(len(flux), dtype=float)
    for i in range(1, len(flux)):
        out[i] = max(0.0, out[i - 1] + flux[i]) if np.isfinite(flux[i]) else out[i - 1]
    return out


def forward_reference(values, quantile=0.98, minimum_prior=365, floor=1e-6):
    x = np.asarray(values, dtype=float)
    reference = np.full(len(x), np.nan)
    for i in range(len(x)):
        prior = x[:i]
        prior = prior[np.isfinite(prior)]
        if len(prior) >= minimum_prior:
            reference[i] = max(floor, float(np.quantile(prior, quantile)))
    return x / reference, reference


def antecedent_precipitation(rainfall, decay=0.90):
    x = np.asarray(rainfall, dtype=float)
    out = np.empty(len(x))
    memory = 0.0
    for i, value in enumerate(x):
        memory = value + decay * memory if np.isfinite(value) else np.nan
        out[i] = memory
    return out


def comparator_indicators(daily, params=None):
    params = params or BWSDParameters()
    result = pd.DataFrame({"Date": daily["Date"], "BWSD": daily["BWSD_formal"]})
    indicators = {
        f"P{w}d": daily["P_mm"].rolling(w, min_periods=1).sum() for w in [3, 7, 15]
    }
    indicators["API0.90"] = antecedent_precipitation(daily["P_mm"])
    for name, values in indicators.items():
        result[name], result[name + "_reference"] = forward_reference(
            values, quantile=params.p_stat
        )
    # The balance variants retain the original BWSD initialization and
    # prior non-critical maximum; rainfall-memory indicators use quantiles.
    for name, loss in [("P-E", "E_mm"), ("P-Q", "Q_mm")]:
        flux = (daily["P_mm"] - daily[loss]).to_numpy()
        result[name] = replay_flux(flux, params, "paper-prior")
        result[name + "_reference"] = storage_from_flux(flux) / result[name]
        indicators[name] = flux
    rows = []
    for name in ["BWSD"] + list(indicators):
        s = result.loc[daily["BWSD_formal"].notna(), name].dropna()
        rows.append(
            {
                "Indicator": name,
                "Valid_days": len(s),
                "Days_ge_0.70": int((s >= 0.70).sum()),
                "Days_ge_1.00": int((s >= 1).sum()),
            }
        )
    return result, pd.DataFrame(rows)


def prediction_metrics(observed, predicted, threshold=0.70):
    obs = np.asarray(observed, dtype=float)
    pred = np.asarray(predicted, dtype=float)
    valid = np.isfinite(obs) & np.isfinite(pred)
    obs = obs[valid]
    pred = pred[valid]
    if not len(obs):
        raise ValueError("No paired observations available")
    o = obs >= threshold
    p = pred >= threshold
    tp = int((o & p).sum())
    fp = int((~o & p).sum())
    fn = int((o & ~p).sum())
    tn = int((~o & ~p).sum())
    denom = np.sum((obs - obs.mean()) ** 2)
    return {
        "N": len(obs),
        "NSE": 1 - float(np.sum((obs - pred) ** 2)) / denom if denom > 0 else np.nan,
        "RMSE": float(np.sqrt(np.mean((obs - pred) ** 2))),
        "F1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else np.nan,
        "CSI": tp / (tp + fp + fn) if tp + fp + fn else np.nan,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
    }


def persistence_diagnostics(daily, formal_start):
    rows = []
    predictions = []
    for lead in [1, 3]:
        frame = pd.DataFrame(
            {
                "Origin_date": daily["Date"],
                "Target_date": daily["Date"].shift(-lead),
                "Observed_BWSD": daily["BWSD_all"].shift(-lead),
                "Predicted_BWSD": daily["BWSD_all"],
            }
        ).dropna()
        test = frame.loc[frame["Target_date"] >= formal_start].copy()
        test["Lead_days"] = lead
        predictions.append(test)
        rows.append(
            {
                "Lead_days": lead,
                "Method": "Persistence",
                "Target": "Hydrological storage state BWSD >= 0.70",
                **prediction_metrics(test["Observed_BWSD"], test["Predicted_BWSD"]),
            }
        )
    return pd.DataFrame(rows), pd.concat(predictions, ignore_index=True)


def parameter_sensitivity(hydrology, params):
    rows = []
    for p in [0.950, 0.975, 0.980, 0.990]:
        for m0 in [1.10, 1.20, 1.30]:
            for mnc in [1.05, 1.10, 1.20, 1.30]:
                output, _, _ = calculate_bwsd(
                    hydrology, replace(params, p_stat=p, m0=m0, m_nc=mnc)
                )
                s = output["BWSD_formal"]
                ix = s.idxmax()
                rows.append(
                    {
                        "p_stat": p,
                        "m0": m0,
                        "m_nc": mnc,
                        "Maximum_BWSD": float(s.loc[ix]),
                        "Peak_date": output.loc[ix, "Date"].strftime("%Y-%m-%d"),
                        "Days_ge_0.70": int((s >= 0.70).sum()),
                        "Days_ge_0.90": int((s >= 0.90).sum()),
                        "Days_ge_1.00": int((s >= 1).sum()),
                    }
                )
    return pd.DataFrame(rows)


def replay_flux(flux, params, threshold_policy="confirmed-high"):
    """Fast complete-data case replay; identical formal denominator to core.

    If every prior value lies below a fixed/field lower bound, its quantile
    cannot control the maximum, so evaluating that quantile can be skipped.
    """
    if not np.isfinite(flux).all():
        raise ValueError("Monte Carlo replay requires complete finite fluxes")
    if threshold_policy not in {"confirmed-high", "paper-prior"}:
        raise ValueError("Unknown Monte Carlo threshold policy")
    delta = storage_from_flux(flux)
    n = len(delta)
    initial = max(
        params.s_min_mm,
        params.m0 * float(delta[: params.formal_initialization_days].max()),
    )
    bwsd = np.empty(n)
    prior_max = -np.inf
    nc_max = -np.inf
    nc_count = 0
    for i in range(n):
        denominator = initial
        nc_minimum = (
            30 if threshold_policy == "paper-prior" else params.min_prior_for_nc
        )
        if nc_count >= nc_minimum:
            denominator = max(denominator, params.m_nc * nc_max)
        if i >= params.min_prior_for_stat and prior_max > denominator:
            denominator = max(denominator, float(np.quantile(delta[:i], params.p_stat)))
        bwsd[i] = delta[i] / denominator
        prior_max = max(prior_max, delta[i])
        if threshold_policy == "paper-prior" or bwsd[i] >= params.theta_1:
            nc_max = max(nc_max, delta[i])
            nc_count += 1
    bwsd[: params.formal_initialization_days] = np.nan
    return bwsd


def monte_carlo(
    hydrology,
    quality,
    params,
    realizations=1000,
    seed=SEED,
    threshold_policy="paper-prior",
):
    """Supplementary Table S6; independent daily multiplicative perturbations."""
    from .validation import parse_boolean

    if realizations < 1:
        raise ValueError("realizations must be positive")
    if params.episode_start or not params.assume_confirmed_noncritical:
        raise ValueError(
            "Monte Carlo fast replay is restricted to the complete confirmed Fengshuwan daily case"
        )
    for column in ["Abnormal_sample", "Debris_flow_event"]:
        if (
            column in hydrology
            and parse_boolean(hydrology[column], len(hydrology)).any()
        ):
            raise ValueError(
                "Monte Carlo case replay does not support abnormal or critical-event samples"
            )
    if (
        "Noncritical_confirmed" in hydrology
        and not parse_boolean(hydrology["Noncritical_confirmed"], len(hydrology)).all()
    ):
        raise ValueError(
            "Monte Carlo case replay requires all responses to be confirmed"
        )
    if "Confirmed_on" in hydrology and not pd.to_datetime(
        hydrology["Confirmed_on"]
    ).reset_index(drop=True).equals(hydrology["Date"].reset_index(drop=True)):
        raise ValueError(
            "Monte Carlo case replay requires daily confirmation without delay"
        )
    if not hydrology["Date"].iloc[0] == params.t0:
        raise ValueError("Monte Carlo case replay requires the dataset to begin at t0")
    if (
        not pd.to_datetime(quality["Date"])
        .reset_index(drop=True)
        .equals(hydrology["Date"].reset_index(drop=True))
    ):
        raise ValueError("Quality flags must align exactly with input dates")
    n = len(hydrology)
    p_known = parse_boolean(quality["P_known"], n)
    e_known = parse_boolean(quality["ET_known"], n)
    observed = parse_boolean(quality["is_obs"], n)
    filled = parse_boolean(quality["is_fill"], n)
    sigmas = [
        np.where(p_known, 0.05, 0.10),
        np.where(observed & ~filled, 0.12, 0.25),
        np.where(e_known, 0.10, 0.20),
    ]
    originals = [
        hydrology[c].to_numpy(dtype=float)
        for c in ["Precipitation_mm", "Runoff_mm", "Evapotranspiration_mm"]
    ]
    rng = np.random.default_rng(seed)
    trajectories = np.empty((realizations, n))
    rows = []
    for i in range(realizations):
        p, q, e = [
            np.maximum(0, v * (1 + np.clip(rng.normal(0, sigma), -0.8, 0.8)))
            for v, sigma in zip(originals, sigmas)
        ]
        values = replay_flux(p - q - e, params, threshold_policy)
        trajectories[i] = values
        peak = int(np.nanargmax(values))
        rows.append(
            {
                "Realization": i + 1,
                "Maximum_BWSD": float(values[peak]),
                "Peak_date": hydrology["Date"].iloc[peak].strftime("%Y-%m-%d"),
                "Critical_reference_days": int((values >= 1).sum()),
            }
        )
    formal = np.arange(n) >= params.formal_initialization_days
    bands = pd.DataFrame(
        {"Date": hydrology["Date"], "Median": np.nan, "P05": np.nan, "P95": np.nan}
    )
    bands.loc[formal, ["Median", "P05", "P95"]] = np.quantile(
        trajectories[:, formal], [0.5, 0.05, 0.95], axis=0
    ).T
    maxima = pd.DataFrame(rows)
    count = int((maxima["Critical_reference_days"] > 0).sum())
    summary = {
        "realizations": realizations,
        "seed": seed,
        "threshold_policy": threshold_policy,
        "realizations_with_critical_reference_exceedance": count,
        "empirical_exceedance_frequency": count / realizations,
        "smallest_nonzero_resolvable_frequency": 1 / realizations,
        "maximum_bwsd_median": float(maxima["Maximum_BWSD"].median()),
        "maximum_bwsd_p05": float(maxima["Maximum_BWSD"].quantile(0.05)),
        "maximum_bwsd_p95": float(maxima["Maximum_BWSD"].quantile(0.95)),
        "interpretation": "Input-propagation ensemble, not a calibrated debris-flow probability or confidence bound.",
    }
    return maxima, bands, summary
