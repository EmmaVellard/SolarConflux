import { BODIES, MODES, validateBundle } from "./model.mjs";
export const STEP_SECONDS = { "1h": 3600, "6h": 21600, "1d": 86400 };
// These sources all retrieve from the service and differ only in the ephemeris backend it
// uses, so they share every date, spacing and sample-count rule.
export const RETRIEVED_SOURCES = ["live", "spice", "prefer-spice"];
export const isRetrieved = (source) => RETRIEVED_SOURCES.includes(source);
export const backendFor = (source) =>
  source === "spice" ? "spice" : source === "prefer-spice" ? "prefer-spice" : "horizons";
export function newPeriod(previous) {
  return {
    id: crypto.randomUUID(),
    name: "",
    source: "live",
    start: previous?.start || "2025-01-01T00:00:00Z",
    end: previous?.end || "2025-01-15T00:00:00Z",
    step: previous?.step || "6h",
    bodies: previous
      ? [...previous.bodies]
      : ["Earth", "Solar Orbiter", "BepiColombo"],
    bundle: null,
    cacheKey: null,
  };
}
export function requestKey(period) {
  return JSON.stringify([
    period.start,
    period.end,
    period.step,
    [...period.bodies].sort(),
    backendFor(period.source),
  ]);
}
export function validatePeriod(p) {
  if (!p.bodies || p.bodies.filter((b) => b !== "Sun").length < 2)
    throw Error(
      "Select at least two spacecraft or planets. The Sun is an optional reference.",
    );
  if (
    new Set(p.bodies).size !== p.bodies.length ||
    p.bodies.some((b) => !BODIES.includes(b))
  )
    throw Error("Select supported bodies only.");
  const start = Date.parse(p.start),
    end = Date.parse(p.end);
  if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end)
    throw Error("Start must be earlier than end.");
  if (!STEP_SECONDS[p.step]) throw Error("Choose a valid sample spacing.");
  if (!["live", "spice", "prefer-spice", "example", "import"].includes(p.source))
    throw Error("Choose a trajectory source.");
  if (isRetrieved(p.source)) {
    if (
      new Date(start).getUTCFullYear() < 1900 ||
      new Date(end).getUTCFullYear() > 2100
    )
      throw Error("Live retrieval supports dates from 1900 to 2100.");
    const seconds = (end - start) / 1000;
    if (seconds % STEP_SECONDS[p.step] !== 0)
      throw Error("The period must be a whole number of sample steps.");
    const count = seconds / STEP_SECONDS[p.step] + 1;
    if (count > 5000 || count * p.bodies.length > 50000)
      throw Error(
        "Use a shorter period or wider spacing: 5,000 samples per body and 50,000 total per period.",
      );
  }
  return p;
}
export function validateSettings(s) {
  if (!s.modes.length)
    throw Error("Select at least one geometry before running.");
  if (s.modes.some((m) => !Object.hasOwn(MODES, m)))
    throw Error("Unsupported geometry.");
  for (const key of [
    "cone",
    "tolerance",
    ...(s.modes.includes("arbitrary") ? ["angle"] : []),
  ])
    if (!Number.isFinite(s[key]) || s[key] < 0 || s[key] > 180)
      throw Error("Angles must be within 0–180°.");
  if (s.cone <= 0 || !Number.isFinite(s.speed) || s.speed <= 0)
    throw Error("Cone width and solar wind speed must be positive.");
  if (
    s.latitude !== null &&
    (!Number.isFinite(s.latitude) || s.latitude < 0 || s.latitude > 180)
  )
    throw Error("Latitude span must be within 0–180°, or blank.");
  return s;
}
export function screenConfig(p, settings, bundle) {
  validateBundle(bundle);
  const notes = bundle.coverage_notes || {};
  const absent = p.bodies.filter((b) => !Object.hasOwn(bundle.trajectories, b));
  // A body the retrieval explained as outside its ephemeris coverage is dropped rather than
  // failing the period; one that is simply missing from an example or imported file is not.
  const unexplained = absent.filter((b) => !notes[b]);
  if (unexplained.length)
    throw Error(
      `This dataset does not include ${unexplained.join(", ")}. Choose JPL Horizons to retrieve these bodies.`,
    );
  const bodies = p.bodies.filter((b) => Object.hasOwn(bundle.trajectories, b));
  if (bodies.filter((b) => b !== "Sun").length < 2)
    throw Error(
      `Only ${bodies.join(", ") || "no bodies"} remain after excluding bodies outside their ephemeris coverage; at least two are needed.`,
    );
  // Take the widest span present, since an individual body may be truncated to its coverage.
  const spans = Object.values(bundle.trajectories).filter((v) => v.length);
  const first = Math.min(...spans.map((v) => Date.parse(v[0].time)));
  const last = Math.max(...spans.map((v) => Date.parse(v.at(-1).time)));
  if (Date.parse(p.start) < first || Date.parse(p.end) > last)
    throw Error(
      "This period extends beyond the dataset. Choose JPL Horizons or use dates within its coverage.",
    );
  return { ...settings, bodies, start: p.start, end: p.end };
}
export function runStatus(periods) {
  if (periods.every((p) => p.status === "complete")) return "complete";
  if (periods.some((p) => p.status === "complete")) return "partial";
  if (periods.some((p) => p.status === "cancelled")) return "cancelled";
  return "failed";
}
export function combinedCSV(periods) {
  const quote = (value) =>
    '"' + String(value ?? "").replaceAll('"', '""') + '"';
  const completed = periods.filter((p) => p.result);
  const first = completed[0];
  if (!first) return "";
  const columns = first.result.csv.split(/\r?\n/)[0].split(",");
  const lines = [["period_id", "period_name", ...columns].join(",")];
  for (const period of completed)
    for (const row of period.result.events)
      lines.push(
        [period.plan.id, period.label, ...columns.map((k) => row[k])]
          .map(quote)
          .join(","),
      );
  return lines.join("\r\n") + "\r\n";
}
