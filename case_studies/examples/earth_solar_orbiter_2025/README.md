# Example: Earth and Solar Orbiter in January 2025

This example demonstrates a reproducible SolarConflux run for screening approximate geometric and Parker-spiral alignments between Earth and Solar Orbiter.

The goal is to provide a small, transparent example that users can run locally to understand the expected SolarConflux workflow and output structure.

## Scientific purpose

This example screens for approximate heliocentric configurations involving Earth and Solar Orbiter over a short time interval in January 2025.

It includes:

- cone alignment screening
- Parker spiral footpoint screening
- combined cone-Parker screening
- optional heliographic latitude filtering
- CSV export
- run metadata export
- optional polar plot generation

## Command

From the root of the repository, run:

```bash
bash case_studies/examples/earth_solar_orbiter_2025/command.sh
```

The script writes outputs to:

```text
case_studies/examples/earth_solar_orbiter_2025/outputs/
```

## Parameters

| Parameter | Value |
| --- | --- |
| Bodies | Earth, Solar Orbiter |
| Start time | 2025-01-01 |
| End time | 2025-01-15 |
| Step | 6h |
| Geometries | cone, parker, coneparker |
| Cone width | 20 degrees |
| Longitude tolerance | 15 degrees |
| Latitude tolerance | 10 degrees |
| Solar wind speed | 400 km/s |

## Expected outputs

This repository includes a generated output set from this example. Re-running the command may update the CSV, metadata, and plot files depending on ephemeris availability and local package changes.

```text
outputs/
└── 2025-01-01_to_2025-01-14/
    ├── 2025-01-01_to_2025-01-14.csv
    ├── run_metadata.json
    └── *.png
```

If no matches are found, SolarConflux still writes a header-only CSV file so automated workflows have a predictable artifact.

## Reproducibility notes

This example is intended to be run from the current version of the SolarConflux repository.

The command script installs the local package with:

```bash
python -m pip install .
```

This ensures that the example uses the local checkout rather than an unrelated installed version.

## External dependencies

This example depends on live trajectory retrieval through JPL Horizons via the scientific Python dependencies used by SolarConflux.

A successful run requires:

- internet access
- valid JPL Horizons coverage for the selected bodies and dates
- a working local Python environment with the SolarConflux dependencies installed

If trajectory retrieval fails, check the network connection, Horizons availability, and the selected date range.

## Scientific limitations

SolarConflux is an approximate screening tool.

The Parker spiral mode uses a simplified ballistic backmapping approximation. It should not be interpreted as a validated heliospheric connectivity model without further scientific review.

In particular, users should review the following assumptions before using the outputs for publication-quality interpretation:

- Parker spiral sign convention
- solar rotation convention
- source-surface radius
- solar wind speed choice
- latitude treatment
- coordinate-frame assumptions

## Suggested use

This example is useful for:

- checking that the CLI works
- understanding the output folder structure
- generating a small reproducible output set
- demonstrating SolarConflux in the main project README
- testing future changes to the package interface

## How to cite

If this example supports research, reports, or presentations, please cite the main SolarConflux repository using the citation metadata provided in the repository-level `CITATION.cff` file.
