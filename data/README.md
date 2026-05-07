# Processed Daily Hydrological Dataset

This folder is used by the BWSD reproducibility script to locate the processed daily hydrological workbook for the Fengshuwan catchment.

The authoritative archived version of the dataset is available on Zenodo:

```text
Wang, T. (2026). Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023–2026 (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20068173
```

## File expected by the script

```text
fengshuwan_processed_daily_hydrology.xlsx
```

## Input sheet

```text
Daily_Data
```

## Required columns

| Column | Description | Unit |
|---|---|---|
| `Date` | Daily date | YYYY-MM-DD |
| `Precipitation_mm` | Processed daily precipitation depth | mm day^-1 |
| `Evapotranspiration_mm` | Processed daily evapotranspiration-loss depth | mm day^-1 |
| `Water_level_m` | Processed outlet water level | m |
| `Runoff_mm` | Processed daily outlet runoff depth converted to catchment-area-averaged water depth | mm day^-1 |

## Study period

The dataset covers the Fengshuwan catchment monitoring period from:

```text
2023-10-12 to 2026-04-06
```

and contains 908 daily observations.

## Use and citation

This dataset is a general processed daily hydrological dataset for the Fengshuwan catchment. It is used in this repository to reproduce the core daily Basin Water Storage Degree calculation, but it may also support other hydrological and geomorphological studies.

If you use this dataset, please cite the Zenodo dataset DOI:

```text
Wang, T. (2026). Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023–2026 (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20068173
```

The Zenodo record should be treated as the authoritative archived dataset version. Any local copy in this GitHub repository is provided only for computational convenience.

## Related code repository

The BWSD reproducibility code repository is available at:

```text
https://github.com/zjusuge/bwsd-fengshuwan-case
```
