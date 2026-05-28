<h1 align="center">SolarConflux</h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-%3E%3D3.9-blue" alt="Python >= 3.9">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License: MIT">
  <img src="https://img.shields.io/badge/status-research%20prototype-orange" alt="Status: research prototype">
  <a href="https://github.com/EmmaVellard/SolarConflux/actions/workflows/tests.yml">
    <img src="https://github.com/EmmaVellard/SolarConflux/actions/workflows/tests.yml/badge.svg" alt="Tests">
  </a>
</p>

**SolarConflux** is a Python research tool for screening heliocentric spacecraft and planetary ephemerides for approximate geometric and Parker-spiral alignments relevant to coordinated solar observations.

It is designed for transparent scientific screening: clear inputs, explicit assumptions, reproducible CSV outputs, run metadata, and lightweight polar plots.

> SolarConflux is intended for observation-planning support and exploratory scientific analysis. It is not a full heliospheric MHD model and should not be used as a validated connectivity model without further scientific review.

## Scientific Motivation

SolarConflux helps identify time intervals when spacecraft and planetary bodies occupy geometries that may be useful for coordinated solar and heliospheric observations.

These configurations can support first-pass studies of solar wind propagation, multi-spacecraft context, and observation opportunities involving missions and bodies such as Solar Orbiter, Parker Solar Probe, BepiColombo, STEREO-A, JUICE, Earth, Venus, Mars, and Jupiter.

The goal is not to replace detailed heliospheric modeling, but to provide a transparent screening tool for finding potentially interesting time windows.

## Features

- Fetch spacecraft and planetary ephemerides through SunPy, Astropy, Astroquery, and JPL Horizons.
- Transform trajectories to a heliocentric frame for alignment screening.
- Detect approximate opposition, quadrature, cone, arbitrary-angle, Parker spiral, and cone-Parker configurations.
- Handle circular longitude comparisons, including 0/360 degree wraparound cases.
- Optionally require matched bodies to remain within a simple heliographic latitude span.
- Save event CSV files with stable column names.
- Save `run_metadata.json` files describing inputs, assumptions, Horizons identifiers, and generated outputs.
- Generate optional polar plots for quick visual inspection.
- Run from either a command-line interface or a Python workflow.
- Include offline synthetic tests for geometry behavior.

## Documentation

Additional documentation:

- [Scientific validation and assumptions](docs/scientific_validation.md)
- [Parker spiral convention](docs/parker_spiral_convention.md)
- [Release plan](docs/release_plan.md)
- [Example workflow: Earth and Solar Orbiter](examples/earth_solar_orbiter_2025/README.md)
- [Validation case: Solar Orbiter and BepiColombo](validation_cases/solar_orbiter_bepicolombo/README.md)
- [Changelog](CHANGELOG.md)

## Installation

From a local checkout:

```bash
git clone https://github.com/EmmaVellard/SolarConflux.git
cd SolarConflux
python -m pip install .
```

SolarConflux requires Python 3.9 or later.

Runtime dependencies include:

- NumPy
- Matplotlib
- Astropy
- SunPy
- Astroquery

Trajectory retrieval requires network access and valid coverage from JPL Horizons.

## CLI Quickstart

Interactive mode:

```bash
solarconflux --interactive
```

Reproducible non-interactive run:

```bash
solarconflux \
  --bodies Earth,Venus,"Solar Orbiter" \
  --start-time "2025-01-01" \
  --end-time "2025-03-01" \
  --step 60m \
  --geometries opposition,quadrature,cone \
  --cone-width 10 \
  --tolerance 10 \
  --latitude-tolerance 5 \
  --output-dir results \
  --save-plots \
  --verbose
```

Parker spiral screening:

```bash
solarconflux \
  --bodies Earth,"Solar Orbiter" \
  --start-time "2025-01-01" \
  --end-time "2025-02-01" \
  --step 60m \
  --geometries parker,coneparker \
  --solar-wind-speed 400 \
  --output-dir results \
  --save-plots
```

Arbitrary-angle screening:

```bash
solarconflux \
  --bodies Earth,Venus,Mars \
  --start-time "2025-01-01" \
  --end-time "2025-03-01" \
  --step 60m \
  --geometries arbitrary \
  --arbitrary-angle 30 \
  --tolerance 10 \
  --output-dir results
```

CLI angle options are given in degrees. Solar wind speed is given in km/s.

## Python Quickstart

```python
from solarconflux import get_trajectories, matching_dates, save_match

body_list = ["Earth", "Venus", "Solar Orbiter"]

trajectories = get_trajectories(
    body_list,
    "2025-01-01",
    "2025-03-01",
    "60m",
)

matches = matching_dates(
    ["cone", "opposition", "quadrature", "arbitrary"],
    body_list,
    trajectories,
    cone_width=10,
    tolerance=10,
    latitude_tolerance_deg=5,
    arbitrary_angle=30,
    angle_unit="deg",
)

save_match(matches, "results")
```

Public angle inputs default to degrees. The lower-level geometry implementation uses radians internally.

## Example Workflow

A reproducible example is provided in:

```text
examples/earth_solar_orbiter_2025/
```

This example screens approximate geometric and Parker-spiral alignments between Earth and Solar Orbiter in January 2025.

To run it from the repository root:

```bash
bash examples/earth_solar_orbiter_2025/command.sh
```

The example demonstrates CLI usage, trajectory retrieval, cone alignment screening, Parker spiral screening, optional latitude filtering, CSV export, metadata export, and optional polar plot generation.

Outputs are written to:

```text
examples/earth_solar_orbiter_2025/outputs/
```

The example depends on live JPL Horizons trajectory retrieval, so it requires internet access and valid ephemeris coverage for the selected bodies and dates.

## Method Summary

For each selected body and time step, SolarConflux retrieves ephemerides and represents trajectories in a heliocentric spherical frame. The tool then screens candidate time windows using circular angular separation in heliolongitude.

Parker spiral modes use a simplified ballistic backmapping approximation from the body longitude to an estimated source-surface footpoint longitude:

```text
phi_source = phi_body + omega_sun * (r_body - r_source_surface) / u_sw
```

where:

- `phi_source` is the estimated source-surface footpoint longitude.
- `phi_body` is the heliolongitude of the body.
- `omega_sun` is the assumed solar rotation rate.
- `r_body` is the heliocentric distance of the body.
- `r_source_surface` is the assumed source-surface radius.
- `u_sw` is the solar wind speed.

Default Parker spiral assumptions currently include:

- Solar rotation period: 25.38 days.
- Source-surface radius: 2.5 solar radii.
- Parker footpoint tolerance: 5 degrees.
- Default solar wind speed: 400 km/s.

## Supported Geometries

| Geometry | Description | Main parameters |
| --- | --- | --- |
| `opposition` | Heliolongitude separation close to 180 degrees | `--tolerance` |
| `quadrature` | Heliolongitude separation close to 90 degrees | `--tolerance` |
| `cone` | Bodies located within a configurable longitude sector | `--cone-width` |
| `arbitrary` | Heliolongitude separation close to a user-defined angle | `--arbitrary-angle`, `--tolerance` |
| `parker` | Approximate Parker spiral footpoint longitude matching | `--solar-wind-speed` |
| `coneparker` | Combined cone and Parker spiral screening | `--cone-width`, `--solar-wind-speed` |

Longitude comparisons use circular angular separation. This means that values near 0 and 360 degrees are treated correctly.

For `quadrature`, the tool uses unsigned circular separation. A 270 degree oriented configuration is therefore treated as equivalent to a 90 degree separation.

For `arbitrary`, angles greater than 180 degrees are interpreted through their equivalent smaller circular separation.

## Optional Latitude Filtering

By default, SolarConflux applies no additional latitude filter.

Set `--latitude-tolerance` in the CLI, or `latitude_tolerance_deg` in Python, to require each candidate group to satisfy:

```text
max(latitude_deg) - min(latitude_deg) <= latitude_tolerance_deg
```

For two bodies, this is equivalent to:

```text
abs(lat1_deg - lat2_deg) <= latitude_tolerance_deg
```

This latitude filter is a simple heliographic proximity screen applied after the longitude-based geometry criterion. It does not change the Parker spiral approximation, source-surface assumptions, solar wind speed handling, or longitude-based geometry definitions.

## Supported Bodies

SolarConflux currently includes metadata for the following bodies:

- BepiColombo
- Solar Orbiter
- PSP
- Stereo-A
- Juice
- Maven
- Messenger
- Juno
- SDO
- SOHO
- ACE
- Venus
- Earth
- Mars
- Jupiter
- Sun

Availability depends on JPL Horizons coverage for the selected body and date range. Some spacecraft have limited valid time windows.

## Outputs

SolarConflux writes outputs into a date-derived folder inside the selected output directory.

Example:

```text
results/
└── 2025-01-01_to_2025-03-01/
    ├── 2025-01-01_to_2025-03-01.csv
    ├── run_metadata.json
    └── *.png
```

If no matches are found, SolarConflux still writes a header-only CSV file so automated workflows have a predictable artifact.

CSV files use a stable column order:

| Column | Description |
| --- | --- |
| `event_id` | Event identifier within the output file |
| `start_time` | Start time of the detected event |
| `end_time` | End time of the detected event |
| `duration_hours` | Event duration in hours |
| `duration_days` | Event duration in days |
| `geometry` | Geometry mode that produced the event |
| `bodies` | Bodies involved in the event |
| `number_of_bodies` | Number of bodies in the event |
| `latitude_tolerance_deg` | Latitude tolerance used, if any |
| `latitude_span_deg` | Latitude span of the event, if available |
| `tolerance_deg` | Angular tolerance used |
| `cone_width_deg` | Cone width used |
| `arbitrary_angle_deg` | Arbitrary angle used, if any |
| `solar_wind_speed_km_s` | Solar wind speed used for Parker modes |

`run_metadata.json` records the SolarConflux package version, input parameters, selected bodies, Horizons identifiers, generated output filenames, and main assumptions.

When `--save-plots` is used, SolarConflux saves polar plots for quick visual inspection. These plots are intended for exploratory analysis and may require manual refinement before use in publication-quality figures.

## Scientific Assumptions and Limitations

SolarConflux is an approximate geometry and connectivity screening tool.

Important assumptions:

- Coordinates are compared in a heliocentric spherical frame after trajectory retrieval.
- Opposition, quadrature, cone, and arbitrary-angle modes compare heliolongitude only.
- All longitude comparisons use circular angular separation.
- Optional latitude filtering uses a simple maximum-minus-minimum latitude span in degrees.
- Parker spiral matching uses a ballistic source-surface footpoint approximation.
- Latitude matching in Parker modes uses a simple latitude tolerance, not a field-line or plasma model.

Known limitations:

- SolarConflux is not a full heliospheric MHD model.
- Horizons queries require network access.
- Horizons coverage depends on the selected body and date range.
- Event detection assumes compatible time sampling across all selected trajectories.
- Optional latitude filtering requires finite latitude values for all bodies in a candidate group.
- Parker spiral behavior should receive scientific review before publication-quality interpretation.
- The Parker spiral sign convention, solar rotation convention, source-surface radius, and latitude treatment should be validated for the intended scientific application.
- Plots are intended for inspection and may need refinement for publications.

## Testing

Run the offline test suite:

```bash
python -m unittest discover -s tests
```

If `pytest` is installed, the same tests can also be run with:

```bash
pytest
```

The offline tests use synthetic trajectories and do not require live Horizons access.

The current test suite includes checks for CLI help behavior, longitude wraparound near 0 and 360 degrees, opposition detection, cone detection, arbitrary-angle detection, optional latitude filtering, CSV export, and metadata export behavior.

Live Horizons checks should be treated separately because they depend on network access and external ephemeris availability.

## Roadmap

Planned improvements include:

- Validate live Horizons retrieval across all supported bodies and date ranges.
- Expand the example gallery with additional validated spacecraft configurations.
- Add continuous integration for automated testing.
- Add more detailed scientific validation notes for Parker spiral assumptions.
- Review Parker spiral sign convention and source-surface assumptions with domain experts.
- Improve packaging metadata for research software distribution.
- Add optional controls for plot format and plot density.

## Citation

If you use SolarConflux in research, reports, presentations, or derived software, please cite the repository using the metadata provided in [`CITATION.cff`](CITATION.cff).

GitHub should display a **“Cite this repository”** button in the sidebar when the `CITATION.cff` file is present.

Suggested citation:

```text
Vellard, E. SolarConflux: Heliocentric geometry and Parker-spiral alignment screening for coordinated solar observations. GitHub repository: https://github.com/EmmaVellard/SolarConflux
```

A DOI may be added later by archiving a release through Zenodo or another research software archive.

## References

Scientific and software context relevant to SolarConflux includes:

- Parker, E. N. (1958). Dynamics of the interplanetary gas and magnetic fields. The Astrophysical Journal.
- JPL Horizons documentation.
- SunPy documentation.
- Astropy documentation.
- Astroquery documentation.

## Credits

Author: Emma Vellard

SolarConflux was developed as a research tool for studying coordinated solar observations using spacecraft and planetary alignments.

## License

SolarConflux is distributed under the MIT License. See `LICENSE` for details.
