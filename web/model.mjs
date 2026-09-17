export const MODES = {
  cone: "Cone",
  parker: "Parker spiral",
  opposition: "Opposition",
  quadrature: "Quadrature",
  coneparker: "Cone + Parker",
  arbitrary: "Custom angle",
};
export const BODIES = [
  "BepiColombo",
  "Solar Orbiter",
  "Europa Clipper",
  "PSP",
  "Stereo-A",
  "Juice",
  "Maven",
  "Messenger",
  "Juno",
  "SDO",
  "SOHO",
  "ACE",
  "Venus",
  "Earth",
  "Mars",
  "Jupiter",
  "Sun",
];
// One colour per entry in BODIES, in the same order, so no two bodies can share one. Six
// colours were cycled here before, which gave the default selection of Earth and Solar
// Orbiter the same colour. Earth, Mars, Jupiter and the Sun take conventional hues; the rest
// are spread across the wheel and also separated by lightness, because 17 hues alone are not
// reliably distinguishable.
export const COLORS = [
  "#467b64", // BepiColombo — dark green
  "#b8862f", // Solar Orbiter — bronze
  "#7f82b0", // Europa Clipper — periwinkle
  "#bf7262", // PSP — terracotta
  "#4e91a2", // Stereo-A — teal
  "#919443", // Juice — olive
  "#8c5b8e", // Maven — plum
  "#b5476b", // Messenger — raspberry
  "#35617f", // Juno — steel blue
  "#74a94e", // SDO — leaf green
  "#a2542a", // SOHO — sienna
  "#574b93", // ACE — violet
  "#2b8f80", // Venus — jade
  "#3d6bb5", // Earth — blue
  "#b4341f", // Mars — red
  "#6b5b3e", // Jupiter — dark bronze
  "#d8ab50", // Sun — gold, matching the central marker
];
export const AU = 149597870.7;
// Must match the Parker defaults in solarconflux/geometries.py (sidereal 25.38 d rotation,
// source surface at 2.5 solar radii), so the drawn spiral is the one the screening used.
export const SOLAR_ROTATION_DAYS = 25.38;
export const OMEGA_SUN = (2 * Math.PI) / (SOLAR_ROTATION_DAYS * 86400);
export const SOURCE_SURFACE_KM = 2.5 * 696000;
export function validateBundle(data) {
  if (
    data?.schema !== "solarconflux.trajectories.v1" ||
    data.frame !== "HeliocentricInertial" ||
    data.time_scale !== "UTC"
  )
    throw Error(
      "Choose an HCI / UTC trajectory JSON exported by SolarConflux with --export-trajectories.",
    );
  const entries = Object.entries(data.trajectories || {});
  if (entries.length < 2 || entries.length > 17)
    throw Error("The file must contain 2–17 bodies.");
  let reference;
  for (const [name, points] of entries) {
    if (!BODIES.includes(name)) throw Error(`Unsupported body: ${name}`);
    if (!Array.isArray(points) || !points.length || points.length > 20000)
      throw Error("Each body needs 1–20,000 samples.");
    const times = points.map((p) => {
      if (
        typeof p.time !== "string" ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(p.time) ||
        !Number.isFinite(Date.parse(p.time))
      )
        throw Error(
          "Sample times must be valid ISO UTC timestamps ending in Z.",
        );
      if (
        ![p.lon_deg, p.lat_deg, p.radius_km].every(
          (x) => typeof x === "number" && Number.isFinite(x),
        ) ||
        Math.abs(p.lat_deg) > 90 ||
        p.radius_km < 0
      )
        throw Error(
          "Coordinates must be finite, radii non-negative, and latitudes within ±90°.",
        );
      return Date.parse(p.time);
    });
    if (times.some((t, i) => i && t <= times[i - 1]))
      throw Error("Sample timestamps must be strictly increasing.");
    if (
      times.length > 2 &&
      times
        .slice(2)
        .some(
          (t, i) => Math.abs(t - times[i + 1] - (times[1] - times[0])) > 1000,
        )
    )
      throw Error(
        "Samples must have uniform spacing. Split files containing gaps.",
      );
    // Bodies need not cover the same interval, because a mission's ephemeris can begin or
    // end inside the requested window; such a body simply takes no part in the geometry
    // outside its own coverage. They must still share a cadence and sit on a common grid,
    // which is what still rejects misaligned samples.
    if (reference && times.length > 1 && reference.length > 1) {
      const cadence = times[1] - times[0];
      if (Math.abs(cadence - (reference[1] - reference[0])) > 1000)
        throw Error("Every body must be sampled at the same cadence.");
      if (Math.abs((times[0] - reference[0]) % cadence) > 1000)
        throw Error("Every body must sit on the same sample grid.");
    }
    if (!reference || times.length > reference.length) reference = times;
  }
  return data;
}
export function validateConfig(c, data) {
  if (c.bodies.length < 2) throw Error("Select at least two bodies.");
  if (!c.modes.length) throw Error("Select at least one alignment geometry.");
  if (c.modes.some((x) => !MODES[x])) throw Error("Unsupported geometry.");
  const samples = Object.values(data.trajectories)[0];
  const start = Date.parse(c.start),
    end = Date.parse(c.end);
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end)
    throw Error("Enter a valid date range, with the start before the end.");
  if (
    start < Date.parse(samples[0].time) ||
    end > Date.parse(samples.at(-1).time)
  )
    throw Error(
      "Choose a date range within the dataset coverage, or import another dataset.",
    );
  if (
    !samples.some(
      (p) => Date.parse(p.time) >= start && Date.parse(p.time) <= end,
    )
  )
    throw Error("No samples fall in this date range.");
  for (const key of [
    "cone",
    "tolerance",
    ...(c.modes.includes("arbitrary") ? ["angle"] : []),
  ])
    if (!Number.isFinite(c[key]) || c[key] < 0 || c[key] > 180)
      throw Error("Angles must be between 0° and 180°.");
  if (c.cone <= 0) throw Error("Cone width must be greater than zero.");
  if (!Number.isFinite(c.speed) || c.speed <= 0)
    throw Error("Solar wind speed must be positive.");
  if (
    c.latitude !== null &&
    (!Number.isFinite(c.latitude) || c.latitude < 0 || c.latitude > 180)
  )
    throw Error("Latitude span must be between 0° and 180°, or blank.");
  return c;
}
export function makeCommand(bodies, start, end, step) {
  const names = [
    ...new Set(
      bodies
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  ];
  if (names.length < 2 || names.some((n) => !BODIES.includes(n)))
    throw Error(
      "Choose at least two supported bodies. Names: " + BODIES.join(", "),
    );
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(start) ||
    !/^\d{4}-\d{2}-\d{2}$/.test(end) ||
    !(Date.parse(start) < Date.parse(end))
  )
    throw Error("Start date must be earlier than end date.");
  if (!["1h", "6h", "1d"].includes(step))
    throw Error("Unsupported sample spacing.");
  const samples =
    (Date.parse(end) - Date.parse(start)) /
      (step === "1h" ? 3600000 : step === "6h" ? 21600000 : 86400000) +
    1;
  if (samples > 20000)
    throw Error(
      "Choose a shorter interval or wider spacing: the browser supports 20,000 samples per body.",
    );
  return `solarconflux \\\n  --bodies '${names.join(",")}' \\\n  --start-time ${start} --end-time ${end} --step ${step} \\\n  --geometries cone,parker,opposition,quadrature \\\n  --export-trajectories --output-dir solarconflux_output`;
}
