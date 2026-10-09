# Methods and implementation map

| Manuscript component | Implementation |
|:--|:--|
| Apparent net input and non-negative storage recursion | `bwsd/core.py:calculate_bwsd` |
| Initialization and prior statistical/non-critical constraints | `bwsd/core.py`, `bwsd/parameters.py` |
| Supplementary Method S1: confirmation and episode embargo | `calculate_bwsd`, optional `Confirmed_on` and episode bounds |
| Rainfall-memory and water-balance comparator indicators | `bwsd/analysis.py:comparator_indicators` |
| Supplementary Table S4: short-lead continuity | `persistence_diagnostics` |
| Supplementary Tables S4–S5: XGBoost/SHAP | `bwsd/attribution.py` |
| Supplementary Table S6: input perturbation | `monte_carlo` |

## Initialization and denominator

Storage is zero at the low-storage reference date; that day's flux is not accumulated. Thereafter `DeltaS[t] = max(0, DeltaS[t-1] + P[t] - Q[t] - E[t])` in millimetres. The fixed bound is `max(s_min, m0 * max(initialization storage))`. The first 90 days are hydrological initialization; the first 365 calendar days establish the bound. The fixed bound uses the completed initialization record: pre-formal BWSD is retrospective and cannot be interpreted as a historical online prediction.

During formal evaluation, the denominator uses only earlier samples. Its statistical term is the `p_stat` quantile of eligible prior storage, after the minimum history size. The non-critical term is `m_nc * max(qualified prior storage)`. A sample qualifies if complete, not abnormal, independently confirmed non-critical and its already frozen BWSD is at least `theta_1`. Confirmation must precede the current decision date. Each component is exposed in the output, as is the controlling component.

The Fengshuwan replay assumes daily confirmation from the monitored no-critical-event case. The public flux workbook does not contain an archive of timestamped field confirmations. For a different catchment set `assume_confirmed_noncritical=false` and supply independently established flags; absence of an event in a spreadsheet is not evidence of non-critical response.

During the 1 June–10 July 2025 embargo, in-episode samples are withheld from both prior reference components until after 10 July. Ratios remain frozen at their decision-time values. This sensitivity check concerns information timing, not real-time warning skill.

## Missing and abnormal records

Dates must be unique and contiguous. Represent a missing day explicitly with NaN fluxes. `carry` holds storage on incomplete-flux days and excludes that day's sample from threshold estimation; `nan` propagates unknown storage thereafter without silently restarting at zero. Neither option reconstructs missing water balance. Abnormal flags exclude samples from reference fitting, but do not automatically correct supplied fluxes. True critical-event flags are rejected because the event-evidence branch is not implemented.

## Comparators, persistence and attribution

P3d, P7d, P15d and API (decay 0.90) use their own prior 0.98-quantile references after 365 prior values. P−E and P−Q storage variants retain the original BWSD initialization and prior non-critical maximum while removing one loss term. Their ≥0.70 or ≥1 counts refer to their own normalized references and are not event false-positive counts.

Persistence predicts BWSD at t+1 or t+3 with BWSD at t. Evaluation is partitioned by target date. F1 and CSI classify the storage state ≥0.70, not debris-flow events. The separate one-day XGBoost regressor is fitted before the formal target-date cutoff and explained by SHAP; imputation is learned on training data only. Its 24 features summarize storage, water-balance forcing, rainfall, drainage, atmospheric loss and seasonality. The training target includes retrospective initialization BWSD; attribution is diagnostic, not validation of a deployed forecast trained online during initialization.

## Hydraulic preprocessing boundary

The processed drainage series was obtained by transforming the original stage record through the compound-weir rating before temporal integration. Supplementary Method S3 gives the 90-degree V-notch, 0.1 m datum and coefficient 1.2974; all processed heads remain within the lower notch. The public code reads the released drainage-equivalent depth. Applying a nonlinear rating directly to daily mean stage would not reproduce the original integrated drainage, so this release deliberately does not do so.
