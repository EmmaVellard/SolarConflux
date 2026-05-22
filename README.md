# SolarConflux

SolarConflux retrieves heliocentric trajectories for spacecraft and planets and screens them for approximate geometric alignments useful in coordinated solar-observation planning.

It is designed as a transparent scientific screening tool: clear inputs, explicit assumptions, reproducible CSV outputs, and lightweight polar plots.

## Features

- Fetch spacecraft and planetary ephemerides through SunPy/JPL Horizons.
- Transform trajectories to a heliocentric frame for alignment screening.
- Detect opposition, quadrature, cone, arbitrary-angle, Parker spiral, and cone-Parker configurations.
- Use circular longitude comparisons so 0/360 degree edge cases are handled correctly.
- Optionally require matched bodies to stay within a simple heliographic latitude span.
- Save event CSV files, run metadata JSON, and optional polar plots.
- Run from Python or from a reproducible command-line interface.

## Installation

From a local checkout:

```bash
python -m pip install .
```

For development and tests:

```bash
python -m pip install ".[dev]"
```

Trajectory retrieval requires the runtime scientific dependencies declared by the package: SunPy, Astropy, Astroquery, NumPy, and Matplotlib. The offline unit tests use synthetic trajectories and do not require live Horizons access.

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
  --geometries parker,coneparker \
  --solar-wind-speed 400 \
  --output-dir results
```

CLI angle options, including `--latitude-tolerance`, are in degrees. Solar wind speed is in km/s. Latitude filtering is optional; omitting it preserves longitude-based matching behavior.

## Python Quickstart

```python
from solarconflux import get_trajectories, matching_dates, save_match

body_list = ["Earth", "Venus", "Solar Orbiter"]
trajectories = get_trajectories(body_list, "2025-01-01", "2025-03-01", "60m")

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

Public angle inputs default to degrees. The optional `latitude_tolerance_deg` parameter is also in degrees. The lower-level `Geometry` class uses radians internally, and `matching_dates(..., angle_unit="rad")` is available for explicit radian inputs.

## Outputs

SolarConflux writes outputs into a date-derived folder such as `results/2025-01-01_to_2025-03-01/`.

CSV files use a stable column order:

| event_id | start_time | end_time | duration_hours | duration_days | geometry | bodies | number_of_bodies | latitude_tolerance_deg | latitude_span_deg | tolerance_deg | cone_width_deg | arbitrary_angle_deg | solar_wind_speed_km_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2025-01-01 00:00:00 | 2025-01-01 02:00:00 | 2 | 0.0833333 | cone | Earth;Venus | 2 | 5 | 4 | 10 | 10 |  | 400 |

No-match runs still write a header-only CSV so automated workflows have a predictable artifact.

`run_metadata.json` records package version, input parameters, body list, Horizons IDs, generated output filenames, and the assumptions used for the run.

Optional polar plots show event windows with clearer titles, body labels, radial units, and visually distinct event markers. PNG is the default plot format; the plotting helper can also save other Matplotlib-supported formats such as PDF.

## Supported Geometries

- `opposition`: heliolongitude separation close to 180 degrees.
- `quadrature`: heliolongitude separation close to 90 degrees. A 270 degree oriented configuration is treated as the same unsigned circular separation.
- `cone`: heliolongitude separation within a configurable cone width.
- `arbitrary`: unsigned circular heliolongitude separation close to a user-specified angle. Angles above 180 degrees are interpreted by their equivalent smaller circular separation.
- `parker`: approximate matching of Parker spiral source-surface footpoint longitude, plus a latitude tolerance.
- `coneparker`: cone alignment and Parker footpoint matching together.

Supported bodies currently include BepiColombo, Solar Orbiter, PSP, Stereo-A, Juice, Maven, Messenger, Juno, SDO, SOHO, ACE, Venus, Earth, Mars, Jupiter, and Sun.

## Optional Latitude Filtering

By default, SolarConflux applies no latitude filter. Longitude-based geometry matches behave as before.

Set `--latitude-tolerance` on the CLI, or `latitude_tolerance_deg` in Python, to require each candidate group to satisfy:

```text
max(latitude_deg) - min(latitude_deg) <= latitude_tolerance_deg
```

For two bodies, this is equivalent to `abs(lat1_deg - lat2_deg) <= latitude_tolerance_deg`.

This is a simple heliographic latitude proximity screen applied after the existing geometry criterion passes. It does not change Parker spiral physics, source-surface assumptions, sign convention, solar wind speed handling, or the longitude-based geometry definitions. For `parker` and `coneparker`, the existing Parker latitude check is preserved; the optional latitude filter is an additional group-level screen when requested.

## Scientific Assumptions And Limitations

SolarConflux is an approximate geometry and connectivity screening tool. It is not a full heliospheric MHD model.

Important assumptions:

- Coordinates are compared in a heliocentric spherical frame after trajectory retrieval is transformed to Heliocentric Inertial coordinates.
- Opposition, quadrature, cone, and arbitrary-angle modes compare heliolongitude only.
- All longitude comparisons use circular angular separation.
- Optional latitude filtering uses a simple max-minus-min latitude span in degrees.
- Parker spiral matching estimates a source-surface footpoint longitude using a ballistic backmapping approximation:

```text
phi_source = phi_body + omega_sun * (r_body - r_source_surface) / u_sw
```

- The default solar rotation period is 25.38 days.
- The default source surface radius is 2.5 solar radii.
- The default Parker footpoint tolerance is 5 degrees.
- Latitude matching in Parker modes uses a simple latitude tolerance, not a field-line or plasma model.

Parker spiral behavior is intentionally documented as approximate and should receive scientific review for sign convention, rotation convention, source-surface assumptions, and latitude treatment before publication-quality interpretation.

Known limitations:

- Horizons queries require network access and valid coverage for each body.
- Event detection assumes all trajectories share the same number of time steps.
- Optional latitude filtering requires finite latitude values for all bodies in a candidate group.
- Plots are intended for quick inspection and may need manual refinement for publication figures.

## Testing

Run the offline test suite:

```bash
python -m unittest discover -s tests
```

If pytest is installed, the same tests are pytest-compatible:

```bash
pytest
```

Live Horizons integration tests are skipped by default. Enable them explicitly:

```bash
SOLARCONFLUX_RUN_INTEGRATION=1 pytest -m integration
```

## Roadmap

- Validate live Horizons retrieval across each supported body and date range.
- Add a small gallery of real example outputs.
- Review Parker spiral sign convention and latitude tolerance with domain experts.
- Add optional controls for plot format and plot density in the CLI.
- Improve packaging metadata for publication workflows.

## Credits

Author: Emma Vellard

SolarConflux was developed as a research tool for studying coordinated solar observations using spacecraft alignments.

License: MIT. See [LICENSE](LICENSE).
