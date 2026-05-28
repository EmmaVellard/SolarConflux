# Parker Spiral Convention

This note documents the Parker spiral convention currently implemented in SolarConflux.
It is intended to make the code behavior explicit and reproducible for researchers reviewing
the package.

SolarConflux uses a simplified ballistic backmapping approximation for Parker spiral screening:

```text
phi_source = phi_body + omega_sun * (r_body - r_source_surface) / u_sw
```

where:

- `phi_source` is the estimated source-surface footpoint longitude.
- `phi_body` is the heliocentric longitude of the body or spacecraft.
- `omega_sun` is the assumed solar rotation rate.
- `r_body` is the heliocentric radial distance of the body or spacecraft.
- `r_source_surface` is the assumed source-surface radius.
- `u_sw` is the solar wind speed.

Distances are converted to meters internally, and `u_sw` is interpreted in meters per second
inside the geometry layer. Public CLI inputs for solar wind speed are given in kilometers per
second and converted before this calculation.

## Default Assumptions

The current defaults are:

- Solar rotation period: 25.38 days.
- Source-surface radius: 2.5 solar radii.
- Default solar wind speed: 400 km/s.
- Parker footpoint tolerance: 5 degrees.

Under the current implementation convention, larger radial distances produce larger longitude
shifts for fixed solar wind speed, and faster solar wind speeds produce smaller longitude shifts
for fixed radial distance.

## Interpretation

This convention is a ballistic backmapping approximation. It is useful for identifying candidate
Parker-spiral-related configurations for follow-up analysis, but it is not a full magnetic
connectivity model and it is not a heliospheric MHD calculation.

SolarConflux Parker and cone-Parker outputs should therefore be described as candidate
Parker-spiral-related configurations, not confirmed magnetic connectivity. Publication-level use
should include additional validation, contextual observations, and domain expert review.

## Review Status

The implemented formula and default parameters are now covered by offline regression tests that
compare `Geometry.parker_spiral_function` against an independent calculation of the documented
formula. These tests validate consistency with the current implementation and documentation.

They do not validate the physical sign convention for every coordinate frame or scientific use
case. The Parker spiral sign convention, coordinate-frame assumptions, and source-surface choice
still require expert review before publication-level interpretation.
