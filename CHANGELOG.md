# Change log

## 1.1.0 — 9 October 2026

- Align article metadata with acceptance and the final title; do not invent an article DOI.
- Replace the monolithic entry point with a reusable package and retain `python main.py` compatibility.
- Add comparative indicators, target-date persistence, parameter sensitivity, episode embargo and 1000-realization uncertainty propagation.
- Add chronological XGBoost/SHAP attribution, additivity checks and optional PNG/PDF diagnostic plots.
- Expose S1 frozen high-storage eligibility, confirmation delays and explicit quality flags. Preserve original Monte Carlo replay as a separate named policy because its helper used all prior non-critical samples.
- Reject malformed data, ambiguous evidence and unsupported critical-event inputs; propagate unknown storage under the NaN policy rather than restarting at zero.
- Correct atmospheric-loss terminology, mark retrospective initialization values and retain original data/output workbooks.
- Add parameter/input contracts, provenance manifests, test coverage and continuous integration.
