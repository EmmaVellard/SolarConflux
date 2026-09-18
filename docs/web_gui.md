# Browser GUI

SolarConflux runs the repository's Python screening engine in a Web Worker using **Pyodide 0.27.7**. The interface is static and compatible with GitHub Pages. A small Python service supplies live trajectories, from JPL Horizons or from SPICE kernels.

## Plan an observation run

1. Name the run and choose a trajectory source for the first period: **JPL Horizons · retrieve live**, **SPICE kernels · retrieve live**, **SPICE where available, else Horizons**, **Bundled January 2025 example**, or **Imported trajectory file**. The three retrieved sources share every date, spacing and sample-count rule and differ only in the ephemeris backend. Choose the mixed option for a period containing Solar Orbiter, PSP, ACE or SDO, which have no usable SPK.
2. Choose dates in UTC, sample spacing, and at least two observing bodies. All 17 catalog bodies are available. The Sun is an optional reference origin and does not participate in alignment groups, so it does not count towards the two.
3. Use **Add period** for another interval or body selection, up to eight periods. Each period has independent dates and bodies; geometry settings below apply to all periods.
4. Choose geometries and tolerances. **Unselect all geometries** clears the geometry selection, and each period's **Unselect all bodies** clears its own bodies. At least one geometry is required to run. Note that the angular tolerance also sets the latitude agreement the Parker modes require.
5. Click **Retrieve & screen**. Live data loads directly into the page. Requests are processed sequentially; retrieved data is reused for unchanged requests. **Refresh trajectories on next run** requests a fresh retrieval, subject to the service cache.
6. Select a period's result, move the sample slider or play the trajectory. Names stay visible beside plotted bodies and in the legend, and each body keeps its own colour. The readout under the plot names the alignment windows containing the displayed sample, so leaving one window and entering another is explicit rather than inferred. Use the table's view buttons to inspect an event.
7. Download the current period's CSV and metadata, or **All periods CSV**, which identifies each period by name and ID.

![Two-period explorer](../images/gui-explorer.jpg)

The chart projects HCI coordinates onto the solar equatorial XY plane. AU annotations refer to projected distance; the legend reports full radius and longitude/latitude. Trajectory lines connect samples; they are not complete orbits or magnetic field lines. Dense paths are simplified for display only; screening uses every sample.

When a Parker or cone-Parker window contains the displayed sample, a dotted curve runs from each matched body inward to the source surface, in that body's colour. It traces the same ballistic backmapping the screening applies, at the wind speed that run used, so two matched bodies visibly converge near the source surface. It assumes one constant radial wind speed and holds latitude fixed, and it is not a modelled magnetic field line.

Bodies need not cover the same interval, because a mission's ephemeris can begin or end inside the requested period. Samples are matched by timestamp, so a body covering only part of the period is drawn only where it has data and is marked as outside its coverage elsewhere, rather than being drawn at another sample's position.

The bundled dataset contains Earth, Solar Orbiter and BepiColombo from 1–15 January 2025 at six-hour cadence (57 samples per body). Selecting bodies or dates absent from an example/import produces an explanatory error. Live mission availability is determined by Horizons, not the catalog's historical coverage hints.

## History and recovery

Runs are saved automatically in **History**, including settings, period definitions, retrieved/imported trajectories, results and errors. Reopening a run restores its saved data without retrieving it again. Completed periods remain available if another period fails or you cancel. Failed and partial runs are identified explicitly.

![Saved runs](../images/gui-history.jpg)

History uses IndexedDB in this browser and is separate for each origin and device. Clearing browser site data deletes it. There is no account or cloud synchronization. **Download run** saves a complete JSON record; backup reimport is not currently supported. **Delete** offers an immediate **Undo**. If browser storage is unavailable, screening still works and result downloads remain available.

Cancellation stops the browser's current request and screening worker. A retrieval already started on the service can finish and populate its cache. Reloading loses an unfinished draft; completed saved runs remain.

## Live retrieval and privacy

JPL's API does not support embedding cross-origin calls in a webpage. Its [API policy](https://ssd-api.jpl.nasa.gov/doc/) calls for serialized requests, caching and backoff. The included service follows that request pattern; public hosting must preserve a single shared query queue.

Only selected body names, UTC interval, cadence and the chosen ephemeris backend go to the configured retrieval service. Imported files, run names, screening settings and history are not uploaded by the GUI. The service reads Horizons through SunPy, or local SPICE kernels through spiceypy, and transforms either to HCI with the same SunPy transform. It caches responses in memory for 24 hours, with bounded memory and entry counts; restarts clear the cache. The hosting provider can log requests and connection information.

Live requests allow dates from 1900–2100, spacing of one hour, six hours or one day, at most 5,000 samples per body and 50,000 total samples. Actual ephemeris coverage can be narrower: a body reaching only part of the period contributes the covered part, a body with no coverage at all is left out, and either way the reason appears in the run feedback and the exported metadata. A period covering none of its bodies fails and names each reason. The GUI presents service errors within the affected period.

The first calculation downloads the pinned Python runtime from jsDelivr. Optional fonts are external downloads. This is not an offline-installed PWA.

## Imported file contract

CLI exports remain available with `--export-trajectories`. Import accepts `solarconflux.trajectories.v1` JSON with `frame: "HeliocentricInertial"`, `time_scale: "UTC"`, and a `trajectories` mapping from supported body names to samples containing `time`, `lon_deg`, `lat_deg` and `radius_km`. See `web/example.json` for a complete real example.

Import validates schema, frame, UTC, supported names, lengths, strictly increasing timestamps, uniform cadence, a shared cadence and sample grid across bodies, finite coordinates, latitude bounds and nonnegative radii. Bodies are not required to cover the same interval or to have equal sample counts, since a mission's ephemeris can begin or end inside the period; they must still sit on one common grid. Limits are 20 MB, 17 bodies and 20,000 samples per body. Source statements remain user-provided and unverified. Metadata identifies the dataset with SHA-256; this is provenance tracking, not an authenticity signature.

Exports round timestamps to the nearest second. Event duration is last matching sample minus first matching sample; single-sample events have zero duration. Sampling does not locate exact threshold crossings. Multi-body groups share a matching anchor and are not necessarily all-pairs alignments.

## Develop and deploy

```sh
python -m unittest discover -s tests
node --test tests/*.test.mjs
python scripts/build_web.py
python -m solarconflux.server --port 8765
```

Open `http://127.0.0.1:8765/`. Rebuild and reload after edits. Serve through HTTP, not `file://`.

The build packages this checkout's Python source into `engine.zip` and generates an integrity manifest. Relative assets support both `/` and `/SolarConflux/`. No npm installation is required. See [deployment instructions](../deploy/README.md) for the live service and GitHub Pages configuration.

## Validation boundary

See [the integrity and usability audit](integrity_usability_audit.md). Functional tests do not establish publication-grade validation of heliospheric magnetic connectivity. Parker conventions and physical interpretation still require independent scientific review.
