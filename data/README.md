# Data and provenance

The original `fengshuwan_processed_daily_hydrology.xlsx` is preserved without modification: 908 daily rows, 12 October 2023–6 April 2026, sheet `Daily_Data`.

Dataset citation: Wang, T. (2026). *Processed Daily Hydrological Dataset for the Fengshuwan Catchment, Zhejiang, China, 2023–2026* (v1.0.0). Zenodo. https://doi.org/10.5281/zenodo.20068173

The area is the 0.8461 km² **study subcatchment**, within the broader Fengshuwan basin. P, Q and E are consistently expressed as daily depths. The archived field `Evapotranspiration_mm` represents an evaporation-based atmospheric water-loss proxy, not measured catchment evapotranspiration. Drainage was transformed from original stage observations before daily aggregation; the released daily stage cannot reconstruct that integration.

`quality_flags.csv` is an author-derived sidecar extracted from the original daily-analysis workbook, aligned to the released dates and verified against its flux series. It restores P_known, ET_known, is_obs and is_fill for Supplementary Table S6 uncertainty propagation. It is newly included in this software release; do not assume it is already contained in the existing Zenodo deposit. See [the dictionary](../docs/data_dictionary.md) and `manifest.json` for hashes and provenance.

Raw instrument records, field confirmation timestamps, photographs and the full manuscript are not redistributed here. Default daily non-critical confirmation is a stated replay assumption for this case, not a substitute for independent evidence at another site.

The code's MIT license does not replace the dataset's license. Consult the Zenodo record for dataset reuse terms and cite the dataset separately from the accepted article.
