#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export SUNPY_CONFIGDIR="${SUNPY_CONFIGDIR:-/private/tmp/solarconflux_sunpy_config}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/private/tmp/solarconflux_mpl_config}"
mkdir -p "$SUNPY_CONFIGDIR" "$MPLCONFIGDIR"

python -m pip install .

solarconflux \
  --bodies BepiColombo,"Solar Orbiter",Earth \
  --start-time "2025-01-01" \
  --end-time "2025-01-15" \
  --step 6h \
  --geometries opposition,quadrature,cone,parker,coneparker \
  --cone-width 15 \
  --tolerance 10 \
  --latitude-tolerance 10 \
  --solar-wind-speed 400 \
  --output-dir validation_cases/solar_orbiter_bepicolombo/outputs \
  --save-plots \
  --plot-format png \
  --verbose
