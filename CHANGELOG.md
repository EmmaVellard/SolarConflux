# Changelog

All notable changes to SolarConflux will be documented in this file.

SolarConflux follows a lightweight versioning approach while it remains a research prototype.

## Unreleased

### Added

- Parker spiral convention documentation and regression tests.

## 0.1.0

Initial research-prototype release.

### Added

- Command-line workflow for heliocentric geometry screening.
- Python workflow for scripted use.
- Support for opposition, quadrature, cone, arbitrary-angle, Parker, and cone-Parker screening.
- Optional heliographic latitude filtering.
- Circular longitude handling near the 0/360 degree boundary.
- CSV export with stable column names.
- Run metadata export through `run_metadata.json`.
- Optional polar plot generation.
- Reproducible Earth and Solar Orbiter example workflow.
- Generated example outputs.
- Scientific validation and assumptions documentation.
- Citation metadata through `CITATION.cff`.
- GitHub Actions workflow for offline tests.
- Project metadata through `pyproject.toml`.

### Notes

SolarConflux is currently a research prototype. Parker spiral and cone-Parker outputs should be interpreted as approximate screening results unless supported by additional scientific validation.
