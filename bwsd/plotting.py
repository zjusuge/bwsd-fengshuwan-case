"""Portable diagnostic plots generated from exported scientific tables."""

from pathlib import Path
import pandas as pd


def plot_diagnostics(daily, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.dates import ConciseDateFormatter, AutoDateLocator

    out = Path(output)
    figures = out / "figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    def save(fig, name):
        fig.savefig(figures / (name + ".png"), dpi=200, bbox_inches="tight")
        fig.savefig(figures / (name + ".pdf"), bbox_inches="tight")
        plt.close(fig)

    def date_axis(ax):
        locator = AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(ConciseDateFormatter(locator))

    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True, layout="constrained")
    for c, label, color in [
        ("P_mm", "Rainfall", "#426b93"),
        ("Q_mm", "Drainage", "#bb663e"),
        ("E_mm", "Atmospheric loss", "#5b8876"),
    ]:
        axes[0].plot(daily["Date"], daily[c], label=label, color=color, lw=0.8)
    axes[0].set_ylabel("Daily water depth (mm)")
    axes[0].legend(ncol=3, frameon=False)
    axes[1].plot(
        daily["Date"], daily["DeltaS_mm"], label="Apparent storage", color="#426b93"
    )
    axes[1].plot(
        daily["Date"], daily["S_crit_minus_mm"], label="Reference", color="#bb663e"
    )
    axes[1].set_ylabel("Water depth (mm)")
    axes[1].legend(frameon=False)
    axes[2].plot(
        daily["Date"], daily["BWSD_all"], color="#a4acb1", label="Pre-formal diagnostic"
    )
    axes[2].plot(
        daily["Date"], daily["BWSD_formal"], color="#426b93", label="Formal BWSD"
    )
    for value in [0.7, 0.9, 1]:
        axes[2].axhline(value, color="#bb663e", ls="--", lw=0.8)
    axes[2].set_ylabel("BWSD")
    axes[2].legend(frameon=False)
    date_axis(axes[2])
    save(fig, "storage_state_overview")
    if (out / "comparator_statistics.csv").exists():
        d = pd.read_csv(out / "comparator_statistics.csv")
        fig, ax = plt.subplots(figsize=(8, 3.5), layout="constrained")
        d.set_index("Indicator")[["Days_ge_0.70", "Days_ge_1.00"]].plot.bar(
            ax=ax, color=["#426b93", "#bb663e"], rot=0
        )
        ax.set_ylabel("Formal-period days")
        ax.set_xlabel("")
        ax.legend(
            ["Normalized level ≥ 0.70", "Normalized reference ≥ 1.00"], frameon=False
        )
        save(fig, "comparator_exceedance")
    if (out / "monte_carlo_bands.csv").exists():
        d = pd.read_csv(out / "monte_carlo_bands.csv", parse_dates=["Date"])
        fig, ax = plt.subplots(figsize=(9, 3.5), layout="constrained")
        ax.fill_between(
            d["Date"],
            d["P05"],
            d["P95"],
            color="#b1cbd8",
            label="5th–95th ensemble percentiles",
        )
        ax.plot(
            daily["Date"],
            daily["BWSD_formal"],
            color="#426b93",
            label="Deterministic BWSD",
            lw=1,
        )
        ax.axhline(1, color="#bb663e", ls="--", lw=0.8)
        ax.set_ylabel("BWSD")
        date_axis(ax)
        ax.legend(frameon=False)
        save(fig, "input_uncertainty")
    if (out / "shap_feature_ranking.csv").exists():
        d = pd.read_csv(out / "shap_feature_ranking.csv").head(12).iloc[::-1]
        fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
        ax.barh(d["Feature"], d["Mean_absolute_SHAP"], color="#426b93")
        ax.set_xlabel("Mean absolute SHAP contribution (BWSD)")
        save(fig, "diagnostic_attribution")
