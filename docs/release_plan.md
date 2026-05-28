# Release Plan

This document defines the planned development direction for SolarConflux.

## Current Status

Current version: `0.1.0`

SolarConflux is currently a research prototype for approximate heliocentric geometry and Parker-spiral alignment screening.

The current release focuses on:

- basic geometry screening
- command-line and Python workflows
- CSV and metadata export
- optional plotting
- reproducible example outputs
- initial documentation and CI

## Next Milestone: v0.2.0

Theme: validation and usability release.

The goal of `v0.2.0` is to make SolarConflux more robust, easier to use, and clearer about its scientific assumptions.

Planned scope:

- improve CLI usability
- add `--list-bodies`
- expose plot format control through the CLI
- strengthen offline geometry tests
- add Parker spiral behavior tests
- improve error messages for invalid inputs and Horizons failures
- document coordinate-frame and Parker spiral assumptions more clearly
- keep live Horizons tests separate from default CI
- maintain generated example outputs

## Future Milestone: v0.3.0

Theme: scientific validation release.

The goal of `v0.3.0` is to improve the scientific defensibility of SolarConflux outputs.

Possible scope:

- independent Parker spiral convention review
- comparison against independently computed spacecraft longitudes
- historical multi-spacecraft event case study
- expert-reviewed notes on Parker and cone-Parker interpretation
- clearer distinction between geometric screening and magnetic connectivity
- optional live integration tests for validated environments

## Out of Scope for Now

The following are intentionally out of scope for the current prototype:

- full heliospheric MHD modeling
- magnetic field-line tracing
- automatic event interpretation
- publication-quality plotting defaults
- claims of confirmed magnetic connectivity

## Release Criteria for v0.2.0

Before tagging `v0.2.0`, the following should be true:

- all offline tests pass in CI
- README examples match the CLI behavior
- example workflow can be rerun locally
- supported body listing is available from the CLI
- Parker spiral behavior tests are present
- scientific assumptions remain clearly documented
