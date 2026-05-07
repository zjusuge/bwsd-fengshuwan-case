# Basin Water Storage Degree BWSD: Fengshuwan Daily Case

This repository provides a lightweight and transparent implementation of the **core daily Basin Water Storage Degree BWSD calculation** for the Fengshuwan small debris-flow catchment in Tianmushan, Zhejiang Province, China.

The processed daily hydrological dataset used by this repository is archived on Zenodo as an independent dataset:

> Wang, T. (2026). *Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023–2026* (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20068173

The repository accompanies the manuscript:

> **Basin Water Storage Degree: A Forward-Looking Water-Balance Indicator for Hydrological-State Warning in Small Debris-Flow Catchments**

The associated manuscript is currently under peer review. A formal journal citation will be updated after publication.

---

## 1. Repository scope

This public repository is designed to reproduce the **core daily BWSD calculation** reported for the Fengshuwan catchment using the processed daily hydrological dataset archived on Zenodo.

The released code reproduces:

- daily apparent net water input;
- apparent basin storage increment;
- forward-looking critical-reference storage threshold;
- BWSD values;
- BWSD-based hydrological-state levels;
- selected exceedance statistics;
- parameter summary;
- metadata;
- output-column dictionary.

The repository is intentionally lightweight. It focuses on the daily no-event Fengshuwan implementation of the BWSD framework.

The following materials are **not fully included** in this public repository:

- raw high-frequency sensor records;
- raw video-monitoring files;
- UAV imagery and field-inspection archives;
- intermediate water-level and discharge-processing files;
- publication-quality figure-generation scripts;
- supplementary indicator-comparison scripts;
- XGBoost and SHAP diagnostic scripts;
- Monte Carlo uncertainty-propagation scripts;
- full sensitivity-analysis scripts.

These materials are retained by the authors and may be provided upon reasonable request where appropriate.

The independent processed daily hydrological dataset is archived on Zenodo and can be reused for broader hydrological and geomorphological research with appropriate citation.

---

## 2. Authors and contact

For questions about the dataset, code, or manuscript, please contact the first author:

**Tianlong Wang**

- Ocean College, Zhejiang University, Zhoushan 316000, China
- School of Civil and Environmental Engineering, Nanyang Technological University, Singapore 637616, Singapore
- Contact: <tianlong_wang@zju.edu.cn>

---

## 3. Repository structure

```text
bwsd-fengshuwan-case/
├── README.md
├── main.py
├── requirements.txt
├── LICENSE
├── CITATION.cff
├── .gitignore
├── data/
│   ├── README.md
│   └── fengshuwan_processed_daily_hydrology.xlsx
└── results/
    └── fengshuwan_bwsd_results.xlsx
```

---

## 4. Input data

The processed daily hydrological dataset used by this repository is archived on Zenodo:

```text
Wang, T. (2026). Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023–2026 (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20068173
```

The input workbook expected by the script is:

```text
data/fengshuwan_processed_daily_hydrology.xlsx
```

The main input sheet is:

```text
Daily_Data
```

The processed daily dataset contains the following variables:

| Column name | Description | Unit |
|---|---|---|
| `Date` | Daily date | yyyy-mm-dd |
| `Precipitation_mm` | Daily precipitation depth | mm day^-1 |
| `Evapotranspiration_mm` | Daily field-measured evapotranspiration-loss depth | mm day^-1 |
| `Water_level_m` | Processed daily outlet water level | m |
| `Runoff_mm` | Daily outlet runoff depth converted to catchment-area-averaged water depth | mm day^-1 |

The released dataset covers the Fengshuwan monitoring period from **12 October 2023 to 6 April 2026** and contains **908 daily observations**.

The Zenodo record should be treated as the authoritative archived version of the processed daily hydrological dataset. The copy included in this GitHub repository, if present, is provided for computational convenience and should remain identical to the Zenodo version.

---

## 5. Output data

Running the public script creates the output workbook:

```text
results/fengshuwan_bwsd_results.xlsx
```

The output workbook contains the following sheets:

| Sheet name | Description |
|---|---|
| `Daily_BWSD` | Daily water-balance variables, apparent storage, forward-looking threshold components, BWSD values, and BWSD-based hydrological-state levels |
| `Exceedance` | Selected exceedance statistics for the formal evaluation period |
| `Parameters` | Fixed parameter values used in the daily Fengshuwan implementation |
| `Metadata` | Basic dataset, implementation, and reproducibility metadata |
| `Column_Dictionary` | Explanation of output columns |

---

## 6. Method summary

### 6.1 Apparent net water input

For the daily implementation, the apparent net water input is calculated as:

$$
I^{*}_{t} = P_{t} - Q_{t} - E_{t}
$$

where:

- \(P_{t}\) is daily precipitation depth;
- \(Q_{t}\) is daily outlet runoff depth;
- \(E_{t}\) is daily field-measured evapotranspiration-loss depth;
- \(I^{*}_{t}\) is the apparent net water input.

All variables are expressed as catchment-area-averaged water depths in millimeters.

---

### 6.2 Apparent basin storage increment

A low-storage reference state is initialized as:

$$
\Delta S_{t_{0}} = 0
$$

The apparent basin storage increment is then recursively updated as:

$$
\Delta S_{t} =
\max
\left(
0,
\Delta S_{t-1} + I^{*}_{t}
\right)
$$

where \(\Delta S_{t}\) is the apparent basin storage increment relative to the selected low-storage reference state.

The non-negative constraint prevents long-term accumulation of nonphysical negative storage values caused by measurement uncertainty, imperfect water-balance closure, or unrepresented subsurface drainage.

---

### 6.3 Forward-looking critical-reference threshold

For each day \(t\), the critical-reference storage threshold is calculated using only information available before that day.

The statistical prior threshold is calculated from prior valid samples:

$$
S^{-}_{stat,t}
=
Q_{p}
\left(
\mathcal{B}_{t-1}
\right)
$$

where:

- \(S^{-}_{stat,t}\) is the forward-looking statistical prior threshold;
- \(Q_{p}\) is a high-quantile operator;
- \(\mathcal{B}_{t-1}\) is the set of valid apparent storage values available before day \(t\).

The no-event Fengshuwan implementation uses the following daily threshold form:

$$
S^{-}_{crit,t}
=
\max
\left(
S_{min},
S_{init},
S^{-}_{stat,t},
S^{-}_{nc,t}
\right)
$$

where:

- \(S^{-}_{crit,t}\) is the forward-looking critical-reference storage threshold;
- \(S_{min}\) is a minimum positive threshold;
- \(S_{init}\) is the initialization lower bound;
- \(S^{-}_{stat,t}\) is the statistical prior threshold;
- \(S^{-}_{nc,t}\) is the forward-looking high-storage non-critical constraint.

Because no debris-flow event was documented during the monitoring period, the event-evidence updating module is inactive in this public daily implementation.

---

### 6.4 Basin Water Storage Degree

BWSD is defined as:

$$
BWSD_{t}
=
\frac{\Delta S_{t}}{S^{-}_{crit,t}}
$$

where:

- \(BWSD_{t}\) is dimensionless;
- \(\Delta S_{t}\) is the apparent basin storage increment;
- \(S^{-}_{crit,t}\) is the forward-looking critical-reference storage threshold.

A value below 1.00 indicates that the apparent storage state remains below the forward-looking critical-reference level. A value equal to or greater than 1.00 indicates critical-reference hydrological-state exceedance.

BWSD should be interpreted as a **hydrological-state warning indicator**, not as a stand-alone deterministic prediction of debris-flow occurrence.

---

### 6.5 BWSD-based hydrological-state levels

The daily BWSD-based hydrological-state level is classified using two management-oriented thresholds, \(\theta_{1}\) and \(\theta_{2}\):

$$
L^{B}_{t}
=
\begin{cases}
0, & BWSD_{t} < \theta_{1} \\
1, & \theta_{1} \leq BWSD_{t} < \theta_{2} \\
2, & \theta_{2} \leq BWSD_{t} < 1.0 \\
3, & BWSD_{t} \geq 1.0
\end{cases}
$$

where:

- \(L^{B}_{t}=0\): normal hydrological state;
- \(L^{B}_{t}=1\): enhanced storage state;
- \(L^{B}_{t}=2\): high-storage sensitive state;
- \(L^{B}_{t}=3\): critical-reference hydrological state.

In the Fengshuwan daily implementation, the management-oriented thresholds are:

```text
theta_1 = 0.70
theta_2 = 0.90
```

These thresholds are used for warning-state classification and risk communication. They should not be interpreted as universal physical critical values for debris-flow initiation.

---

## 7. Forward-looking information control

A key feature of BWSD is the strict forward-looking threshold design.

For each calculation day \(t\):

1. the threshold \(S^{-}_{crit,t}\) is calculated first;
2. only information available before day \(t\) is used;
3. the current storage value \(\Delta S_{t}\) is not used to update the threshold for the same day;
4. current-day field response and later confirmation are excluded from the current decision;
5. confirmed evidence can affect only subsequent thresholds.

This design avoids information leakage and circular threshold evaluation.

---

## 8. Main Fengshuwan daily results reproduced by this repository

The public daily calculation reproduces the main no-event BWSD sequence for the Fengshuwan catchment.

Key reported values include:

| Quantity | Value |
|---|---:|
| Monitoring period | 12 October 2023 to 6 April 2026 |
| Number of daily observations | 908 |
| Formal forward-looking evaluation period | 11 October 2024 to 6 April 2026 |
| Number of formal-period BWSD values | 543 |
| Cumulative precipitation | 2955.9 mm |
| Cumulative field-measured evapotranspiration loss | 1459.9 mm |
| Cumulative outlet runoff depth | 1294.1 mm |
| Long-term apparent residual | 201.9 mm |
| Maximum apparent basin storage increment | 473.1 mm on 26 June 2025 |
| Maximum formal-period BWSD | 0.936 on 22 June 2025 |
| Critical-reference exceedance days | 0 |

The June 2025 wetting episode was the closest approach to the critical-reference level during the monitoring period. BWSD briefly exceeded 0.90 but remained below 1.00, consistent with independent field confirmation of non-critical catchment response.

---

## 9. Installation

The code requires Python 3.9 or later.

Install the required Python packages with:

```bash
pip install -r requirements.txt
```

The expected packages are:

```text
numpy
pandas
openpyxl
```

---

## 10. Reproduction

From the repository root, run:

```bash
python main.py
```

The script reads:

```text
data/fengshuwan_processed_daily_hydrology.xlsx
```

and writes:

```text
results/fengshuwan_bwsd_results.xlsx
```

After running the script, check the `Metadata` and `Parameters` sheets in the output workbook to confirm the calculation settings and input dataset DOI.

---

## 11. Notes on interpretation

The released BWSD sequence supports the non-event component of warning-indicator evaluation, including:

- forward-looking non-critical consistency;
- threshold stability;
- seasonal interpretability;
- high-storage non-critical discrimination;
- zero critical-reference exceedance during the formal no-event evaluation period.

The current monitoring record contains no documented debris-flow event. Therefore, this repository does not quantify:

- hit rate;
- missed-alarm rate;
- false-alarm rate;
- critical success index for debris-flow events;
- operational warning lead time;
- complete event-detection skill.

Those evaluations require future monitoring with documented debris-flow events, independent catchments, and higher-temporal-resolution observations.

---

## 12. Relationship to the manuscript

This repository supports the reproducibility of the **core daily BWSD calculation** in the Fengshuwan case study.

The manuscript additionally discusses:

- rainfall-memory indicators;
- API-type indicators;
- simplified water-balance variants;
- June 2025 high-storage non-critical interpretation;
- XGBoost short-lead diagnostic prediction;
- SHAP interpretation;
- sensitivity analysis;
- Monte Carlo uncertainty propagation;
- field evidence from video monitoring, UAV observations, channel-condition inspection, and manual reconnaissance.

These additional analyses are part of the broader manuscript workflow but are not fully included in this lightweight public repository.

---

## 13. Citation 

The associated manuscript is currently under peer review, and a formal journal citation is not yet available.

If you use the processed daily hydrological dataset, please cite the Zenodo dataset:

```text
Wang, T. (2026). Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023–2026 (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20068173
```

BibTeX entry for the dataset:

```bibtex
@dataset{wang2026_fengshuwan_hydrology,
  author    = {Wang, Tianlong},
  title     = {Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023--2026},
  year      = {2026},
  version   = {v1.0.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20068173},
  url       = {https://doi.org/10.5281/zenodo.20068173}
}
```

---

## 14. License

This repository is released under the license specified in the `LICENSE` file.

Unless otherwise stated, the software code and repository documentation are released under the MIT License.

The processed daily hydrological dataset is archived separately on Zenodo and is governed by the license specified in the Zenodo record. Please cite the Zenodo dataset DOI when using the data.

---

## 15. Contact

For questions, data clarification, or collaboration inquiries, please contact:

**Tianlong Wang**  
Ocean College, Zhejiang University, Zhoushan 316000, China  
School of Civil and Environmental Engineering, Nanyang Technological University, Singapore 637616, Singapore  
Email: <tianlong_wang@zju.edu.cn>
