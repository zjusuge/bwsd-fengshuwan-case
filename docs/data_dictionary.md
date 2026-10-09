# Data dictionary

## Required input

| Field | Unit | Meaning |
|:--|:--|:--|
| Date | daily calendar date | Unique, contiguous, timezone-naive observations |
| Precipitation_mm | mm/day | Processed rainfall depth |
| Evapotranspiration_mm | mm/day | Archived name for an evaporation-based atmospheric water-loss proxy; not measured catchment ET |
| Water_level_m | m | Processed outlet stage; retained for context, not reconverted into daily drainage |
| Runoff_mm | mm/day | Stage-derived integrated drainage normalized by the 0.8461 km² study-subcatchment area |

Non-negative finite values or explicit NaNs are accepted. The loader sorts dates but rejects duplicates and gaps. The lower-level calculation API requires ordered dates. CSV and the `Daily_Data` Excel sheet share the schema.

## Optional evidence

`Abnormal_sample`, `Debris_flow_event` and `Noncritical_confirmed` accept explicit true/false or 1/0. `Confirmed_on` records when a response was confirmed and cannot precede its observation. With no confirmation dates, the replay assumes confirmation on the observation date; it is usable only from the following day. A true critical-event flag raises an error because this case implementation does not implement event-evidence mixing.

## Quality sidecar

`data/quality_flags.csv` contains Date, P_known, ET_known, is_obs and is_fill. ET_known retains the historical label for the atmospheric-loss term. It is used for uncertainty standard deviations, not as an additional observational series or an event label. Dates must exactly match the main dataset.

## Main output

`DeltaS_mm` is apparent storage; `S_init_mm`, `S_stat_minus_mm`, `S_nc_minus_mm` and `S_crit_minus_mm` expose the denominator components. `Threshold_control` names the controlling component. `Non_event_threshold_sample` records frozen high-storage eligibility, not whether a debris-flow occurred. `Preformal_retrospective_diagnostic` marks initialization values. `BWSD_formal` is available only after initialization; raw `BWSD_all` is never capped. `BWSD_plot` and `BWSD_0_1` are optional display aliases and must not be used for numerical maxima or exceedance analyses. Hydrological levels 0/1/2/3 use 0.70/0.90/1.00; they are not calibrated debris-flow warning classes.

The workbook provides Daily_BWSD, Exceedance, Parameters, Metadata and Column_Dictionary sheets. CSV/JSON files additionally record comparative analyses, predictions, sensitivity, uncertainty, attribution and execution provenance.
