"""Chronological one-day XGBoost/SHAP attribution (Supplementary Tables S4-S5)."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from .analysis import prediction_metrics, SEED


def predictor_frame(daily):
    work = pd.DataFrame(
        {
            "Date": daily["Date"],
            "BWSD_t": daily["BWSD_all"],
            "DeltaS_t": daily["DeltaS_mm"],
            "Scrit_t": daily["S_crit_minus_mm"],
            "Istar_t": daily["I_star_mm"],
        }
    )
    groups = {
        "Storage-state memory": ["BWSD_t", "DeltaS_t", "Scrit_t"],
        "Current water-balance forcing": ["Istar_t"],
        "Rainfall-memory forcing": [],
        "Runoff-drainage memory": [],
        "Atmospheric-loss memory": [],
        "Net-input memory": [],
        "Seasonality": ["DOY_sin", "DOY_cos"],
    }
    for source, prefix, group in [
        ("P_mm", "P", "Rainfall-memory forcing"),
        ("Q_mm", "Q", "Runoff-drainage memory"),
        ("E_mm", "E", "Atmospheric-loss memory"),
        ("I_star_mm", "Istar", "Net-input memory"),
    ]:
        for w in [3, 7, 15, 30]:
            col = prefix + str(w)
            work[col] = daily[source].rolling(w, min_periods=1).sum()
            groups[group].append(col)
    for w in [7, 15]:
        col = "RC" + str(w)
        work[col] = work["Q" + str(w)] / work["P" + str(w)].replace(0, np.nan)
        groups["Runoff-drainage memory"].append(col)
    doy = work["Date"].dt.dayofyear.astype(float)
    work["DOY_sin"] = np.sin(2 * np.pi * doy / 365.25)
    work["DOY_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return work, groups


def run_attribution(daily, formal_start, destination):
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from xgboost import XGBRegressor
        import shap
    except ImportError as exc:
        raise ImportError(
            'Install the analysis extra: pip install ".[analysis]"'
        ) from exc
    work, groups = predictor_frame(daily)
    features = [c for c in work if c != "Date"]
    work["Target_date"] = work["Date"].shift(-1)
    work["Target_BWSD"] = daily["BWSD_all"].shift(-1)
    sample = work.dropna(subset=["Target_date", "Target_BWSD"]).sort_values(
        "Target_date"
    )
    train = sample.loc[sample["Target_date"] < formal_start]
    test = sample.loc[sample["Target_date"] >= formal_start]
    if len(train) < 60 or len(test) < 30:
        raise ValueError(
            "Insufficient chronological training/evaluation samples; no automatic fallback changes the paper protocol"
        )
    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            (
                "model",
                XGBRegressor(
                    n_estimators=600,
                    max_depth=3,
                    learning_rate=0.020,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    min_child_weight=3,
                    reg_lambda=2.0,
                    reg_alpha=0.05,
                    objective="reg:squarederror",
                    random_state=SEED,
                    n_jobs=1,
                ),
            ),
        ]
    )
    pipeline.fit(train[features], train["Target_BWSD"])
    prediction = pipeline.predict(test[features])
    xtrain = pipeline["imputer"].transform(train[features])
    xtest = pipeline["imputer"].transform(test[features])
    explainer = shap.TreeExplainer(pipeline["model"], data=xtrain)
    values = np.asarray(explainer.shap_values(xtest))
    base = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    if values.shape != xtest.shape or not np.allclose(
        base + values.sum(axis=1), prediction, atol=1e-5
    ):
        raise ValueError("SHAP additivity or shape check failed")
    out = Path(destination)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"Feature": features, "Mean_absolute_SHAP": np.abs(values).mean(axis=0)}
    ).sort_values("Mean_absolute_SHAP", ascending=False).to_csv(
        out / "shap_feature_ranking.csv", index=False
    )
    pd.DataFrame(
        [
            {
                "Group": g,
                "Mean_absolute_SHAP_sum": float(
                    np.abs(values[:, [features.index(c) for c in cols]])
                    .sum(axis=1)
                    .mean()
                ),
            }
            for g, cols in groups.items()
        ]
    ).to_csv(out / "shap_group_ranking.csv", index=False)
    explanations = pd.DataFrame(values, columns=features)
    explanations.insert(0, "Target_date", test["Target_date"].to_numpy())
    explanations.to_csv(out / "shap_values.csv", index=False)
    predictions = pd.DataFrame(
        {
            "Origin_date": test["Date"],
            "Target_date": test["Target_date"],
            "Observed_BWSD": test["Target_BWSD"],
            "Predicted_BWSD": prediction,
        }
    )
    predictions.to_csv(out / "xgboost_diagnostic_predictions.csv", index=False)
    selected = test["Target_date"].eq(pd.Timestamp("2025-06-22")).to_numpy()
    if selected.any():
        index = int(np.flatnonzero(selected)[0])
        pd.DataFrame(
            {
                "Feature": features,
                "Value_at_origin": xtest[index],
                "SHAP": values[index],
            }
        ).to_csv(out / "shap_local_20250622.csv", index=False)
    metadata = {
        "role": "Hydrological attribution only; not an event-warning model",
        "target": "BWSD at t+1",
        "training_samples": len(train),
        "evaluation_samples": len(test),
        "split_on": "Target_date",
        "formal_start": str(formal_start.date()),
        "seed": SEED,
        "n_jobs": 1,
        "features": features,
        "training_last_target_date": str(train["Target_date"].max().date()),
        "evaluation_first_target_date": str(test["Target_date"].min().date()),
        "SHAP_expected_value": base,
        "SHAP_max_additivity_error": float(
            np.max(np.abs(base + values.sum(axis=1) - prediction))
        ),
        "metrics": prediction_metrics(test["Target_BWSD"], prediction),
    }
    (out / "attribution_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return metadata
