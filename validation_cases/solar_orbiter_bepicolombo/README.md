# Validation Case: Solar Orbiter and BepiColombo

This validation case runs SolarConflux on a real-mission configuration involving Solar Orbiter, BepiColombo, and Earth.

The purpose is to exercise the command-line workflow, live trajectory retrieval, output structure, and approximate geometry screening on scientifically relevant spacecraft. It does not validate magnetic connectivity or establish a shared solar-wind source region.

This repository includes generated output files from running the workflow locally.

## Purpose

This case checks that SolarConflux can:

- retrieve real Horizons trajectories for multiple supported bodies;
- screen approximate opposition, quadrature, cone, Parker, and cone-Parker configurations;
- write reproducible CSV and metadata outputs;
- generate quick-look plots when matches are present;
- record the assumptions and run parameters needed for later inspection.

## Bodies

The selected bodies are:

- BepiColombo
- Solar Orbiter
- Earth

The selected interval, 2025-01-01 to 2025-01-15, falls within the repository metadata coverage for both BepiColombo and Solar Orbiter. Earth uses the Horizons planetary identifier listed in the body metadata.

## Command

Run the validation workflow from any directory with:

```bash
bash validation_cases/solar_orbiter_bepicolombo/command.sh
```

The script moves to the repository root, installs the local package, and writes outputs under:

```text
validation_cases/solar_orbiter_bepicolombo/outputs/
```

## Parameters

| Parameter | Value |
| --- | --- |
| Bodies | BepiColombo, Solar Orbiter, Earth |
| Start time | 2025-01-01 |
| End time | 2025-01-15 |
| Step | 6h |
| Geometries | opposition, quadrature, cone, parker, coneparker |
| Cone width | 15 degrees |
| Longitude tolerance | 10 degrees |
| Latitude tolerance | 10 degrees |
| Solar wind speed | 400 km/s |
| Plot format | PNG |

## Generated Outputs

The workflow writes:

- a CSV event table;
- a `run_metadata.json` file with inputs, assumptions, Horizons IDs, and generated filenames;
- PNG quick-look plots when matched events are present.

If no matches are detected for a future rerun, SolarConflux should still write a header-only CSV and metadata file.

## Scientific Interpretation

Outputs from this validation case should be interpreted as approximate screening results. Parker and cone-Parker rows identify candidate Parker-spiral-related configurations under SolarConflux's current ballistic backmapping convention.

They should not be described as confirmed magnetic connectivity.

## Limitations

- The workflow depends on live Horizons availability and network access.
- The Parker spiral convention remains an approximate ballistic screen and still requires expert review before publication-level interpretation.
- The latitude filter is a simple heliographic proximity screen, not field-line tracing.
- Plots are quick-look diagnostics rather than publication-quality figures.
