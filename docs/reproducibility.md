# Reproducibility audit

## Source basis

Version 1.1.0 was reconciled against the accepted clean R1 manuscript, its Supplementary Material, the original daily-storage notebook and the Section 5 figure-generation notebook. The original processed workbook and published-repository reference workbook are preserved byte for byte. The quality sidecar restores the provenance flags used in Supplementary Table S6 from the original daily-analysis workbook.

Persistence NSE reproduces the manuscript values at their reported three-decimal precision; exact CSV values are retained for auditing.

The release rebuilds numerical diagnostics and supplies clear diagnostic plots. It does not claim pixel-identical reproduction of manuscript panels, access to unreleased high-frequency records, or operational event-warning validation.

## Deterministic checks

The initialization bound, full formal storage/denominator/BWSD trajectory, peak dates, exceedance counts, comparator counts and 1-/3-day persistence results are checked against the archived workbook or reported numerical values. The revised core also exposes high-storage evidence eligibility, delayed confirmation and episode embargo. Eligibility flags and pre-formal non-critical components differ from the simplified legacy public implementation; formal ratios in this case remain unchanged.

## Monte Carlo policies: preserve the distinction

Both modes draw 1000 independent daily multiplicative perturbations with PCG64, seed 20260505, in P, Q, E order, clipping perturbations to ±0.8. Standard deviations are 0.05/0.10 for known/uncertain rainfall, 0.10/0.20 for known/uncertain atmospheric loss, and 0.12/0.25 for directly observed/non-filled versus other drainage samples. Each realization rebuilds storage and its initialization/reference trajectory.

The original figure-generation helper used **all prior non-critical storage samples** for its non-critical maximum. This policy, `paper-prior`, reproduces maximum-BWSD median 0.931068 and 5th–95th percentiles 0.904406–0.949092. It is the default Monte Carlo replay, solely to reproduce the reported figure-generation workflow.

Supplementary Method S1 additionally specifies qualification using a frozen high-storage state. `confirmed-high` applies that rule within every perturbed trajectory, activating the field constraint after at least one qualified response. It does not impose the legacy helper's 30-sample minimum on the subset of qualified responses: S1 specifies 30 samples for the statistical prior, not for high-storage field evidence. With the main case parameters, the two policies reproduce the same deterministic formal trajectory and the same 1000 Monte Carlo realization maxima to numerical precision. Other margins and evidence configurations need not be equivalent; the policy is recorded in every run.

```bash
python -m bwsd --analysis --mc-policy paper-prior --output results/generated/paper/bwsd.xlsx
python -m bwsd --analysis --mc-policy confirmed-high --output results/generated/qualified/bwsd.xlsx
```

Both runs have zero critical-reference exceedance realizations in this adopted ensemble. Zero out of 1000 is an empirical frequency, not a zero risk estimate or a confidence bound; 0.001 is the smallest nonzero resolvable frequency. Perturbations omit correlated/systematic errors, unmeasured exchanges and event-model uncertainty.

## Attribution environment

`requirements-paper.txt` records the versions in Supplementary Table S3. Current environments are written into each manifest. This release fixes the documented hyperparameters, random seed and chronological target-date split; it uses one CPU worker for reproducibility and checks SHAP additivity. The original TreeExplainer background sampling behavior is retained. Library versions and background sampling can affect individual SHAP values; rankings explain model behavior, not causal identification.

## Repeatable checks

```bash
pip install -e ".[analysis,dev]"
pytest -q
python -m bwsd --analysis --attribution --plots
```

Tests include causal prefix invariance after initialization, exclusion of current-day evidence from its denominator, confirmation delays, malformed input rejection, missing-data propagation, critical-event rejection, full formal trajectory regression and independent Monte Carlo-kernel checks. The GitHub Actions workflow runs core tests on two Python versions and an analysis smoke run. Reference results and the local verification report are stored separately from generated output.
