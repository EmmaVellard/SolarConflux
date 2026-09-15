# Integrity and usability audit — 14 September 2026

## Scope and conclusion

Reviewed the local checkout and the matching public `main` revision `20f37b5e655164e59e16e7a455a9f1fc5d30817e`, then implemented and tested the static browser GUI and the fixes below.

**Functional conclusion:** the tested Python retrieval/screening/export workflow and browser screening path work. This is an engineering assessment of specified cases, not certification that every ephemeris or scientific interpretation is correct. Parker matching remains an approximate research method requiring independent physical validation.

## Confirmed issues repaired

| Issue | Effect before the repair | Repair and evidence |
| --- | --- | --- |
| Different timestamps at the same array index | Could compare bodies at different times | Reject mismatched timestamps; regression test |
| Reversed or duplicate sample times | Could create misleading event bounds | Require strictly increasing timestamps; regression test |
| Extra trajectories beyond the selected body list | Unselected bodies could enter results | Select only requested trajectories before screening; regression test |
| Nonfinite longitude/radius and invalid latitude | Could silently suppress matches or propagate invalid geometry | Validate normalized coordinates and source-surface radius; regression tests |
| Overlapping events with different end dates | CSV folder could end before the longest event; CSV and plot folders could differ | Folder uses the minimum start and maximum end over all events; regression test |
| Sub-millisecond time conversion residual | Exact boundary displayed as the previous second/date | Round exported UTC timestamps to the nearest second; regression test |
| Incomplete run metadata | Requested interval and Parker constants were absent | Record requested start/end, frame, UTC and model constants |
| Invalid numeric CLI input checked after retrieval | Unnecessary external queries before rejection | Validate numeric inputs before querying Horizons; mocked-network regression test |
| Aware/naive datetime comparison | Some otherwise valid ranges raised a TypeError | Normalize parsed datetimes to UTC before comparison |

The timestamp precision change can change existing event text by one second. Historical committed examples have not been rewritten.

## Automated checks

- Baseline: 53 tests discovered, 52 passed, one live integration test skipped.
- Updated suite: **78 Python tests passed**, with `SOLARCONFLUX_RUN_INTEGRATION=1 SOLARCONFLUX_RUN_HTTP_TESTS=1`, Python 3.12 and installed runtime dependencies.
- **17 JavaScript tests passed** for imported coordinates, schema, coverage, numeric limits, period planning, cache keys, partial-run status and combined exports.
- `pip check`: no broken requirements.
- Python static-site build and JavaScript syntax checks passed.

Commands:

```sh
SOLARCONFLUX_RUN_HTTP_TESTS=1 SOLARCONFLUX_RUN_INTEGRATION=1 .venv/bin/python -m unittest discover -s tests
.venv/bin/python -m pip check
node --test tests/*.test.mjs
python scripts/build_web.py
```

## Real ephemeris check

Retrieved Earth (399), Solar Orbiter (-144) and BepiColombo (-121) using SunPy / JPL Horizons, transformed to HCI, for 2025-01-01 through 2025-01-15 with 6-hour spacing. The bundled `web/example.json` records source, retrieval timestamp, original request and rounded UTC samples. There are 57 samples per body. Installed versions at this check: NumPy 2.5.3, Matplotlib 3.11.2, Astropy 8.0.1, SunPy 8.0.0 and Astroquery 0.4.11.

With cone width 20°, angular tolerance 15°, latitude span 10° and solar wind 400 km/s:

- Cone: Earth–Solar Orbiter, 1–15 January, **336 hours**.
- Quadrature: BepiColombo–Earth, 1–2 January, **24 hours**.
- Parker, cone-Parker and opposition: no windows in this configuration.

CLI CSV, metadata, trajectory JSON and PNG generation completed. The browser's Python worker reproduced the cone and quadrature windows. The old example's apparently different date range was the output-folder bug, not a change to the cone interval.

This test uses one ephemeris service and does not independently validate its coordinate solution. Orbit positions, event counts and Parker results may change with other data coverage, cadence and thresholds.

## Browser usability and data boundaries

- Real Python screening in a worker, using the source packaged from this checkout.
- Parameters invalidate old results and disable stale exports.
- Correct geometry filtering, including a no-windows message.
- Downloaded CSV verified on disk: the cone row spans 336 hours. Downloaded metadata verified on disk: dataset SHA-256 matches the imported/bundled file and records all 57 samples per body.
- Valid local JSON import and malformed-schema rejection; current dataset retained on failure.
- Direct live retrieval from the page through the Python service: Earth/Solar Orbiter/BepiColombo for 1–15 January 2025 and Earth/Venus for 1–3 January, both at six-hour spacing. Both periods completed and were saved together.
- History persisted across reload and restored saved trajectories/results. All 17 catalog bodies are selectable, but live availability was not exhaustively tested for every mission.
- Unselect all geometries clears all six controls and prevents an empty screening.
- A missing Venus trajectory in the bundled example produced a partial run: the valid period remained available and the failing period showed an explicit explanation. History delete and undo were exercised.
- Fixed native date values losing validity after source changes; distinct date ranges were rerun successfully.
- Service tests cover request validation, caching, busy/backoff responses, the Sun reference, HTTP endpoints and origin restrictions.
- Labels, keyboard-accessible controls, semantic tables, status announcements and native dialogs.
- Desktop and phone responsive layouts; detailed interaction evidence is scoped to the tested Chromium-based in-app browser.
- Browser imports additionally require uniform cadence, preventing silent grouping across irregular gaps.
- Import limits: 20 MB, 2–17 supported bodies, up to 20,000 samples each.
- History is browser-local IndexedDB. The retrieval backend receives only selected bodies, dates and cadence; imported files and history are not uploaded. Pyodide and optional fonts are external downloads.
- Persistent plotted captions, visible body legends, cream/green favicon and Emma Vellard credit.
- The engine ZIP is checked against a same-origin SHA-256 manifest. This detects inconsistent builds; it is not protection against a compromised hosting origin. Pyodide is version-pinned, not vendored.

## Remaining limitations

1. Scientific validation of Parker conventions and source connectivity remains open; software tests do not close it.
2. The body catalog's historical coverage hints are not a current mission-availability database. Horizons controls actual availability.
3. Multi-body groups are anchor-based, not all-pairs cliques; the GUI explains this explicitly.
4. Event bounds follow samples, with no interpolation or uncertainty estimate. Missing epochs cannot be reconstructed.
5. Browser provenance strings are user-supplied. A dataset hash identifies the file but does not authenticate it.
6. First-use runtime loading needs network access. Live Horizons requests require a reachable Python retrieval service; GitHub Pages alone cannot provide it.
7. Safari, Firefox, physical iOS/Android devices and screen-reader testing have not been performed. No formal WCAG conformance claim is made.

## Retrieval service limitations

The service serializes outbound queries within one process, bounds requests and cache memory, and backs off after failures. It needs a reverse proxy with HTTPS and public request limits when deployed. CORS is not authentication. Container hosting, multiple-user load and a deployed public endpoint have not been tested. Cancellation in the browser does not cancel an already-running upstream retrieval.

The Sun is represented as the HCI origin and excluded from alignment groups because its observing longitude is undefined. At least two non-Sun bodies are required in the GUI.

## Deployment

The GitHub Pages workflow builds tested static assets on `main`. All asset paths are relative to support the repository subpath. Public deployment is a separate check from local tests; see the task delivery for the actual publication status. Repository Pages must use GitHub Actions as its source.

Publication attempt: the connected GitHub app returned HTTP 403 (`Resource not accessible by integration`) for the tree write. Local Git publishing also lacks usable authentication, and the available browser is signed out. No remote changes were made. The Pages URL returned HTTP 404 before this work; public deployment remains blocked by authentication/permissions.
