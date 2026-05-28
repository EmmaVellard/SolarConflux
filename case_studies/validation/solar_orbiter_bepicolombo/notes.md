# Solar Orbiter and BepiColombo Validation Notes

## Run Summary

This validation case runs SolarConflux for BepiColombo, Solar Orbiter, and Earth over 2025-01-01 to 2025-01-15 using a 6-hour step.

The selected geometries are opposition, quadrature, cone, Parker, and cone-Parker. The run uses a 15 degree cone width, 10 degree longitude tolerance, 10 degree latitude tolerance, and 400 km/s solar wind speed.

## Files Generated

Inspect the output directory with:

```bash
find case_studies/validation/solar_orbiter_bepicolombo/outputs -maxdepth 4 -type f
```

Expected generated artifacts include:

- a CSV file containing the detected event table or headers if no matches are found;
- `run_metadata.json` with input parameters, body list, Horizons IDs, assumptions, and generated filenames;
- PNG quick-look plots when matching events are present.

The committed local run generated:

```text
outputs/
└── 2025-01-01_to_2025-01-07/
    ├── 2025-01-01_to_2025-01-07.csv
    ├── run_metadata.json
    └── cone/
        └── cone_events_001-001_2025-01-01_to_2025-01-07.png
```

The output folder name reflects the detected event span, not the full requested run interval.

## Quick Inspection Checklist

- Confirm the CSV contains stable column names such as `geometry`, `bodies`, `start_time`, `end_time`, `latitude_tolerance_deg`, and `solar_wind_speed_km_s`.
- Confirm `run_metadata.json` records BepiColombo, Solar Orbiter, and Earth.
- Confirm generated plot filenames, if present, are listed in metadata.
- Confirm the date range and step match the command script.
- Confirm no local caches or build artifacts are mixed into the validation output.

## Geometry Interpretation Notes

Opposition, quadrature, and cone rows represent approximate heliolongitude screening results. They are useful for identifying candidate time windows for follow-up review, not for proving causal or physical linkage.

## Parker Spiral Interpretation Notes

Parker and cone-Parker rows use SolarConflux's current ballistic source-surface footpoint approximation. These rows should be described as candidate Parker-spiral-related configurations only.

Do not interpret Parker or cone-Parker rows as confirmed magnetic connectivity without additional analysis.

## Known Limitations

- The workflow depends on live JPL Horizons access.
- The Parker spiral sign convention, source-surface radius, and coordinate assumptions still require expert scientific review for publication-level use.
- The latitude condition is a simple geometric filter.
- The generated plots are quick-look diagnostics.

## Follow-Up Scientific Checks

- Compare retrieved longitudes against an independent ephemeris workflow.
- Review Parker footpoint longitudes with a heliophysics domain expert.
- Compare candidate intervals against in-situ plasma and magnetic-field measurements.
- Check whether any candidate intervals overlap known coordinated-observation campaigns.
