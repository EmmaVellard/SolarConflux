#!/usr/bin/env bash
set -euo pipefail

# Reproducible SolarConflux example:
# Earth and Solar Orbiter, January 2025.
#
# This script can be run from anywhere. It automatically moves to the
# repository root before installing and running SolarConflux.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

python -m pip install .

solarconflux \
  --bodies Earth,"Solar Orbiter" \
  --start-time "2025-01-01" \
  --end-time "2025-01-15" \
  --step 6h \
  --geometries cone,parker,coneparker \
  --cone-width 20 \
  --tolerance 15 \
  --latitude-tolerance 10 \
  --solar-wind-speed 400 \
  --output-dir examples/earth_solar_orbiter_2025/outputs \
  --save-plots \
  --verbose
