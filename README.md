# NDC Nigeria Election Information System

A static, browser-based election operations dashboard for the Nigeria Democratic Congress (NDC). The map combines supplied polling-unit, state, LGA, House constituency and Senate district files with historical 2019/2023 constituency summaries and a WorldPop 2026 age/sex population context layer.

## Run and publish

Open `index.html` through a local HTTP server (for example, `python -m http.server 8000`) or enable **Settings → Pages → Build and deployment → GitHub Actions**. The included workflow deploys the static dashboard to GitHub Pages from `main`; the expected URL is `https://zubairgis.github.io/nigeria/` once Pages is enabled.

The dashboard does not require a database or API key. Map tiles and MapLibre GL JS load from external public services, so an internet connection is needed.

## Map and data

- Blue points are polling units name-matched to a supplemental Google Places-derived file and filtered to a broad Nigeria bounding box. They are candidate locations, not verified INEC coordinates. The current conservative normalized-name matching run found **97,569** units (two more than the previously reported 97,567; the matching and coordinate filter are reproducible in `scripts/prepare_data.py`).
- Red points cover the other **79,277** units. The exact ward-name match places a representative point inside the matched operational ward polygon (36,410 rows); where the ward label could not be matched, the point falls back to an LGA (36,747 rows) or state (6,120 rows) representative point. Those are clearly identified by `location_status` and `coordinate_source`; they are not polling-unit coordinates. All point features retain the supplied state/LGA/ward/polling-unit fields, `lat`, `lng`, `full_code`, and `portal_id`.
- House constituency polygons include `party_2019`, `party_2023`, `Reg_Voters`, `Elig_Voter`, `PollingUni`, `Wards` and `LGAs`. The election fields are winning-party summaries, not candidate vote totals. Voter figures come from the attached source table and must not be treated as a 2027 voter register.
- Senate district boundaries display supplied district attributes and winner/candidate fields; the attached Senate file does not provide a matching 2019/2023 result series.
- LGA boundaries in `Nig_LGA.json` are EPSG:32632 and are converted to WGS84 by the preparation script. The submitted state, House and Senate boundaries are retained in WGS84.
- `LGA_Nigeria.json`, `Nig_LGA.json`, `Nig_Elections.json`, `Nig_Elections_2019.json`, `Nig_Senate_Elections.json`, `States.json` and the NDC logo are the user-provided files. `Nig_Elections_2019.json` is an exact duplicate of `Nig_Elections.json`.

## WorldPop 2026 age and sex

`data/processed/constituency_age_sex_2026.csv` contains male/female age-band summaries aggregated from WorldPop Nigeria 2026 1 km age/sex estimates (R2025A v1) to the 360 supplied House constituencies. `estimated_population_18_plus` uses 40% of the 15–19 bin plus all bins age 20 and above. This is a rough population estimate, not a count of registered or eligible voters. WorldPop source data are modelled estimates and should be interpreted accordingly.

To reproduce the CSV in Google Colab, use `colab_worldpop_2026.ipynb`, or run:

```bash
python -m pip install rasterio shapely numpy
python scripts/aggregate_worldpop_2026.py
```

The script downloads the official 1 km archive (about 244 MB) into `data/source/` if it is not already present. The archive is ignored by Git; only the compact processed CSV is committed.

## Polling-agent registration

A KoboToolbox XLSForm and its external polling-unit choice CSV are in `kobo/`. The form cascades State → LGA → Ward → Polling Unit and collects name, age and mobile number. See [`kobo/README.md`](kobo/README.md) for deployment steps. Fill in the data-controller contact and retention period before collecting real responses.

Names, ages, phone numbers and response exports are sensitive personal information in a political-organization context. Keep Kobo submissions in a private Kobo project. Do not commit them to this public repository.

## Sources and attribution

- Polling-unit attributes: [saidiadegoke/nigeria-inec-geo](https://github.com/saidiadegoke/nigeria-inec-geo), `data/polling-units.csv`.
- Supplemental polling-unit coordinates: [mykeels/inec-polling-units](https://github.com/mykeels/inec-polling-units), based on Google Places results and not verified against INEC GPS. Coordinate attribution and filtering details are retained in each feature.
- Operational ward polygons: [NGA Ward Boundaries Feature Service](https://services1.arcgis.com/XBhYkoXKJCRHbe7M/ArcGIS/rest/services/NGA_Ward_Boundaries/FeatureServer/0). This operational layer is used for approximate map placement only, not authoritative polling-unit coordinates or a legal boundary determination.
- Age/sex population estimates: [WorldPop Nigeria Age and Sex Structures](https://www.worldpop.org/), 2026, R2025A v1, 1 km urban-adjusted product; see [`scripts/aggregate_worldpop_2026.py`](scripts/aggregate_worldpop_2026.py) for the exact download URL and aggregation method. Attribute WorldPop and its data license when redistributing.
- The supplied election and administrative boundaries and logo are included as uploaded by the project owner; verify their source dates, completeness and usage rights before external publication.

## Important limits

This is an information and planning dashboard. It is not an official INEC system, a verified polling-unit GPS database, a 2027 result prediction, or a voter register. Verify records and boundary provenance before operational use. The public repository contains geography and aggregate summaries only; keep all agent response data private.
