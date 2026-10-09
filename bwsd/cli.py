"""Reproducible command-line workflow and machine-readable provenance."""

import argparse, hashlib, json, platform
from pathlib import Path
from dataclasses import asdict
from importlib.metadata import version, PackageNotFoundError
import pandas as pd
from .parameters import BWSDParameters
from .core import calculate_bwsd
from .io import (
    load_daily_hydrology,
    write_results,
    build_parameters_table,
    build_column_dictionary,
    print_key_results,
)

ROOT = Path(__file__).resolve().parents[1]


def json_safe(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    raise TypeError(type(value).__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reproduce BWSD storage-state assessment and manuscript diagnostics."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/fengshuwan_processed_daily_hydrology.xlsx",
    )
    parser.add_argument("--sheet", default="Daily_Data")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/generated/fengshuwan_bwsd_results.xlsx",
    )
    parser.add_argument(
        "--config", type=Path, help="JSON parameter overrides; dates use YYYY-MM-DD"
    )
    parser.add_argument(
        "--analysis",
        action="store_true",
        help="Indicators, persistence, sensitivity, embargo and Monte Carlo",
    )
    parser.add_argument(
        "--quality-flags", type=Path, default=ROOT / "data/quality_flags.csv"
    )
    parser.add_argument("--mc-realizations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260505)
    parser.add_argument(
        "--mc-policy",
        choices=["paper-prior", "confirmed-high"],
        default="paper-prior",
        help="Original paper Monte Carlo replay or Supplementary S1 eligibility",
    )
    parser.add_argument(
        "--attribution",
        action="store_true",
        help="Optional chronological XGBoost/SHAP analysis",
    )
    parser.add_argument(
        "--plots", action="store_true", help="Optional matplotlib diagnostic figures"
    )
    args = parser.parse_args(argv)
    if args.mc_realizations < 1 or args.seed < 0:
        parser.error(
            "Monte Carlo realizations must be positive and the seed non-negative"
        )
    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
    if "t0" in config:
        config["t0"] = pd.Timestamp(config["t0"])
    params = BWSDParameters(**config)
    hydrology = load_daily_hydrology(args.input, args.sheet)
    if args.analysis and (
        params.t0 != pd.Timestamp("2023-10-12")
        or params.formal_initialization_days != 365
    ):
        parser.error(
            "The bundled analysis profile uses Fengshuwan dates and a 365-day initialization; run the core for other configurations"
        )
    daily, exceedance, metadata = calculate_bwsd(hydrology, params)
    out = args.output.parent
    out.mkdir(parents=True, exist_ok=True)
    write_results(
        daily,
        exceedance,
        build_parameters_table(params),
        metadata,
        build_column_dictionary(),
        args.output,
    )
    daily.to_csv(out / "daily_bwsd.csv", index=False)
    exceedance.to_csv(out / "exceedance.csv", index=False)
    if args.analysis:
        from dataclasses import replace
        from .analysis import (
            comparator_indicators,
            persistence_diagnostics,
            parameter_sensitivity,
            monte_carlo,
        )

        indicators, stats = comparator_indicators(daily, params)
        indicators.to_csv(out / "comparator_indicators.csv", index=False)
        stats.to_csv(out / "comparator_statistics.csv", index=False)
        metrics, predictions = persistence_diagnostics(daily, params.formal_start)
        metrics.to_csv(out / "persistence_metrics.csv", index=False)
        predictions.to_csv(out / "persistence_predictions.csv", index=False)
        parameter_sensitivity(hydrology, params).to_csv(
            out / "parameter_sensitivity.csv", index=False
        )
        embargo, _, _ = calculate_bwsd(
            hydrology,
            replace(params, episode_start="2025-06-01", episode_end="2025-07-10"),
        )
        embargo.to_csv(out / "episode_embargo.csv", index=False)
        quality = pd.read_csv(args.quality_flags)
        maxima, bands, summary = monte_carlo(
            hydrology, quality, params, args.mc_realizations, args.seed, args.mc_policy
        )
        maxima.to_csv(out / "monte_carlo_maxima.csv", index=False)
        bands.to_csv(out / "monte_carlo_bands.csv", index=False)
        (out / "monte_carlo_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
    if args.attribution:
        from .attribution import run_attribution

        run_attribution(daily, params.formal_start, out)
    if args.plots:
        from .plotting import plot_diagnostics

        plot_diagnostics(daily, out)
    packages = {}
    for name in [
        "numpy",
        "pandas",
        "openpyxl",
        "matplotlib",
        "scikit-learn",
        "xgboost",
        "shap",
    ]:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            pass
    provenance = {
        "software_version": "1.1.0",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "parameters": asdict(params),
        "accepted_article": "IJDRR-D-26-01829R1",
        "accepted_date": "2026-10-09",
        "formal_results_only_are_forward_looking": True,
        "data_quality_flags_sha256": (
            hashlib.sha256(args.quality_flags.read_bytes()).hexdigest()
            if args.analysis
            else None
        ),
        "analyses": {
            "analysis": args.analysis,
            "attribution": args.attribution,
            "plots": args.plots,
            "mc_realizations": args.mc_realizations if args.analysis else None,
            "seed": args.seed,
            "mc_policy": args.mc_policy,
        },
    }
    (out / "run_manifest.json").write_text(
        json.dumps(provenance, indent=2, default=json_safe), encoding="utf-8"
    )
    print_key_results(metadata, args.output)
    print("Manuscript diagnostics saved to", out)
