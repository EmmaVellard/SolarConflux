# Scientific Validation and Assumptions

This document summarizes the scientific assumptions, validation status, and appropriate interpretation of SolarConflux outputs.

SolarConflux is an approximate screening tool for identifying potentially useful heliocentric spacecraft and planetary configurations. It is intended to support exploratory analysis and coordinated-observation planning. It is not a full heliospheric MHD model and does not provide validated magnetic connectivity on its own.

## Purpose of SolarConflux

SolarConflux is designed to answer questions such as:

> During a selected time interval, are there approximate heliocentric geometries between selected spacecraft and/or planets that may be interesting for coordinated solar observations?

SolarConflux can help identify candidate time windows for further investigation, but its outputs should be interpreted as screening results rather than definitive physical connections.

SolarConflux is not designed to determine by itself:

- whether a spacecraft is magnetically connected to a specific solar source region
- whether plasma measured at multiple spacecraft comes from the same solar event
- the full heliospheric magnetic-field topology
- the MHD evolution of solar-wind streams or coronal mass ejections
- definitive solar-wind propagation paths

Those questions require additional physical modeling, observations, and domain-specific validation.

## Current Validation Status

Current status: **research prototype**

SolarConflux currently includes:

- deterministic geometry screening based on heliolongitude comparisons
- circular angular separation handling near 0 and 360 degrees
- optional heliographic latitude filtering
- approximate Parker spiral footpoint screening
- reproducible CSV exports
- run metadata exports
- offline synthetic tests for selected geometry behavior
- a reproducible example workflow using Earth and Solar Orbiter

The basic geometry logic can be tested with deterministic synthetic cases. The Parker spiral and cone-Parker modes require additional scientific validation before publication-level interpretation.

## Coordinate and Geometry Assumptions

SolarConflux retrieves or represents trajectories in a heliocentric spherical frame and screens configurations using angular relationships.

The main geometry checks use heliolongitude only unless optional latitude filtering is enabled.

### Longitude treatment

Longitude comparisons use circular angular separation.

For example, longitudes of 359 degrees and 1 degree are treated as being separated by 2 degrees, not 358 degrees.

This is important for events that occur near the 0/360 degree boundary.

### Latitude treatment

Latitude filtering is optional.

When enabled, SolarConflux applies a simple group-level latitude span criterion:

```text
max(latitude_deg) - min(latitude_deg) <= latitude_tolerance_deg
```

For two bodies, this is equivalent to:

```text
abs(lat1_deg - lat2_deg) <= latitude_tolerance_deg
```

This is a geometric proximity filter. It is not magnetic field-line tracing.

## Supported Geometry Definitions

| Geometry | Screening criterion | Interpretation |
| --- | --- | --- |
| `opposition` | Heliolongitude separation close to 180 degrees | Candidate opposite-longitude configuration |
| `quadrature` | Heliolongitude separation close to 90 degrees | Candidate quadrature configuration |
| `cone` | Bodies located within a configurable heliolongitude sector | Candidate common-sector configuration |
| `arbitrary` | Heliolongitude separation close to a user-defined angle | Candidate custom-angle configuration |
| `parker` | Approximate Parker spiral footpoint longitude matching | Candidate ballistic Parker-spiral-related configuration |
| `coneparker` | Combined cone and Parker screening | Candidate configuration satisfying both criteria |

These geometries are useful for screening. They do not automatically imply physical connectivity or causal relationships.

## Parker Spiral Approximation

SolarConflux uses a simplified ballistic backmapping approximation for Parker spiral screening:

```text
phi_source = phi_body + omega_sun * (r_body - r_source_surface) / u_sw
```

where:

- `phi_source` is the estimated source-surface footpoint longitude
- `phi_body` is the body heliolongitude
- `omega_sun` is the assumed solar rotation rate
- `r_body` is the heliocentric distance of the body
- `r_source_surface` is the assumed source-surface radius
- `u_sw` is the solar wind speed

Default assumptions currently include:

- solar rotation period: 25.38 days
- source-surface radius: 2.5 solar radii
- default solar wind speed: 400 km/s
- default Parker footpoint tolerance: 5 degrees

## Parker Spiral Assumptions Requiring Scientific Review

The Parker spiral implementation should be reviewed before being used for scientific conclusions.

Key items requiring validation are:

1. **Sign convention**

   Confirm that the longitude shift has the correct sign for the selected coordinate system and solar rotation convention.

2. **Solar rotation convention**

   Confirm that the selected solar rotation period is appropriate for the intended application.

3. **Source-surface radius**

   Confirm whether 2.5 solar radii is an appropriate default for the targeted use cases.

4. **Solar wind speed**

   Confirm whether a constant solar wind speed is acceptable for the intended screening problem.

5. **Latitude treatment**

   Confirm whether simple latitude tolerance is useful for screening, while clearly documenting that it is not magnetic field-line tracing.

6. **Coordinate frame consistency**

   Confirm that the coordinate frame and longitude convention are appropriate for the intended heliophysical interpretation.

## Scientific Limitations

SolarConflux has the following known limitations:

- it is not a full heliospheric MHD model
- it does not perform magnetic field-line tracing
- it uses simplified geometric and ballistic assumptions
- Parker spiral results depend strongly on solar wind speed and sign convention
- latitude filtering is a simple geometric screen
- Horizons availability depends on body and date range
- output plots are intended for inspection and may need refinement for publication figures

## Appropriate Scientific Interpretation

When describing SolarConflux outputs, use cautious language such as:

> SolarConflux identified candidate time intervals with approximate heliocentric geometric alignment.

or:

> SolarConflux provided a screening of possible Parker-spiral-related configurations under a simplified ballistic backmapping assumption.

Avoid stronger claims unless supported by additional validation, such as:

- confirmed magnetic connectivity
- validated solar-wind propagation path
- physically demonstrated shared source region
- definitive heliospheric linkage

## Recommended Use

SolarConflux is most appropriate for:

- identifying candidate coordinated-observation windows
- exploring approximate spacecraft and planetary geometries
- generating reproducible screening tables
- producing quick-look polar plots
- supporting further investigation with more detailed physical models

SolarConflux outputs should be combined with additional context before being used for scientific interpretation, including:

- in-situ plasma and magnetic-field measurements
- remote-sensing observations
- solar-wind speed estimates
- event timing analysis
- domain expert review
- independent heliospheric modeling when needed

## Summary

SolarConflux is useful as a transparent screening tool for coordinated solar-observation planning. Its geometry logic can be validated with deterministic synthetic tests, while Parker spiral and cone-Parker modes require additional physical review before publication-level interpretation.
