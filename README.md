# SolarConflux

SolarConflux is a Python tool for retrieving heliocentric trajectories of spacecraft and planets and detecting approximate geometric alignments relevant to coordinated solar observations.

It currently supports opposition, quadrature, cone, arbitrary-angle, Parker spiral, and cone-Parker alignment screening.

If you use this tool in scientific work, please cite or acknowledge the repository and author.

## Installation

From a local checkout:

```bash
python -m pip install .
```

For development and tests:

```bash
python -m pip install ".[dev]"
```

Trajectory retrieval requires the runtime scientific dependencies declared by the package: SunPy, Astropy, Astroquery, NumPy, and Matplotlib. The unit tests use synthetic trajectories and do not require live Horizons access.

## Quickstart: CLI

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
  --output-dir results \
  --no-plots \
  --verbose
```

Parker spiral example:

```bash
solarconflux \
  --bodies Earth,"Solar Orbiter" \
  --start-time "2025-01-01" \
  --end-time "2025-02-01" \
  --geometries parker,coneparker \
  --solar-wind-speed 400 \
  --output-dir results
```

CLI angle options are in degrees. Solar wind speed is in km/s.

## Python API Example

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
    arbitrary_angle=30,
    angle_unit="deg",
)

save_match(matches, "results")
```

The lower-level `Geometry` class uses radians internally. The public `matching_dates` helper accepts degrees by default and supports `angle_unit="rad"` for explicit radian inputs.

## Supported Bodies

Supported body names are currently:

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

SolarConflux validates names before querying Horizons and raises a clear error for unsupported bodies.

## Supported Geometries

- `opposition`: heliolongitude separation close to 180 degrees.
- `quadrature`: heliolongitude separation close to 90 degrees. A 270 degree oriented configuration is treated as the same unsigned circular separation.
- `cone`: heliolongitude separation within a configurable cone width.
- `arbitrary`: unsigned circular heliolongitude separation close to a user-specified angle. Angles above 180 degrees are interpreted by their equivalent smaller circular separation.
- `parker`: approximate matching of Parker spiral source-surface footpoint longitude, plus a latitude tolerance.
- `coneparker`: cone alignment and Parker footpoint matching together.

All longitude comparisons use circular angle wrapping, so cases near 0/360 degrees are handled explicitly.

## Scientific Assumptions And Limitations

SolarConflux is an approximate geometry and connectivity screening tool. It is not a full heliospheric MHD model.

Important assumptions:

- Coordinates are compared in a heliocentric spherical frame after trajectory retrieval is transformed to Heliocentric Inertial coordinates.
- Opposition, quadrature, cone, and arbitrary-angle modes compare heliolongitude only.
- Parker spiral matching estimates a source-surface footpoint longitude using a ballistic backmapping approximation:

```text
phi_source = phi_body + omega_sun * (r_body - r_source_surface) / u_sw
```

- The default solar rotation period is 25.38 days.
- The default source surface radius is 2.5 solar radii.
- The default Parker footpoint tolerance is 5 degrees.
- Latitude matching in Parker modes uses a simple latitude tolerance, not a field-line or plasma model.

Known limitations:

- Horizons queries require network access and valid coverage for each body.
- Event detection assumes all trajectories share the same number of time steps.
- Plots are intended for quick inspection and may need manual refinement for publication figures.
- The Parker sign convention and rotation convention should be reviewed for each science use case before publication-quality interpretation.

## Outputs

SolarConflux writes a CSV file in a date-derived output folder. The CSV includes:

- start time;
- end time;
- duration in hours;
- geometry;
- bodies involved;
- number of bodies;
- tolerance;
- cone width;
- arbitrary angle;
- solar wind speed.

The CLI also writes `run_metadata.json` with input parameters, package version, body list, Horizons IDs, and scientific assumptions.

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

## Credits

Author: Emma Vellard

SolarConflux was developed as a research tool for studying coordinated solar observations using spacecraft alignments.

License: MIT. See [LICENSE](LICENSE).
