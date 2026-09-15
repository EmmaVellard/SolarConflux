import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { validateBundle, validateConfig, makeCommand } from "../web/model.mjs";
const sample = JSON.parse(
  fs.readFileSync(new URL("../web/example.json", import.meta.url), "utf8"),
);
const config = {
  bodies: ["Earth", "Solar Orbiter"],
  modes: ["cone"],
  start: "2025-01-01T00:00:00Z",
  end: "2025-01-15T00:00:00Z",
  cone: 20,
  tolerance: 15,
  speed: 400,
  latitude: 10,
  angle: 30,
};
test("real dataset validates with all 57 samples", () =>
  assert.equal(
    Object.values(validateBundle(sample).trajectories)[0].length,
    57,
  ));
test("rejects invalid provenance frame and schema", () => {
  assert.throws(() => validateBundle({ ...sample, frame: "GSE" }));
  assert.throws(() => validateBundle({ ...sample, schema: "v2" }));
});
test("rejects nonfinite coordinates and unmatched times", () => {
  const data = structuredClone(sample);
  data.trajectories.Earth[1].radius_km = Infinity;
  assert.throws(() => validateBundle(data));
  data.trajectories.Earth[1].radius_km = 1;
  data.trajectories.Earth[1].time = "2025-01-01T06:00:01Z";
  assert.throws(() => validateBundle(data));
});
test("requires two bodies and one mode", () => {
  assert.throws(() => validateConfig({ ...config, bodies: ["Earth"] }, sample));
  assert.throws(() => validateConfig({ ...config, modes: [] }, sample));
});
test("rejects out of coverage dates and zero wind", () => {
  assert.throws(() =>
    validateConfig({ ...config, end: "2026-01-01T00:00:00Z" }, sample),
  );
  assert.throws(() => validateConfig({ ...config, speed: 0 }, sample));
});
test("empty latitude disables the optional filter", () =>
  assert.equal(
    validateConfig({ ...config, latitude: null }, sample).latitude,
    null,
  ));
test("command rejects shell injection and unknown bodies", () =>
  assert.throws(() =>
    makeCommand("Earth,$(whoami)", "2025-01-01", "2025-01-15", "6h"),
  ));
test("command includes export with safe body quoting", () =>
  assert.match(
    makeCommand("Earth,Solar Orbiter", "2025-01-01", "2025-01-15", "6h"),
    /--bodies 'Earth,Solar Orbiter'[\s\S]*--export-trajectories/,
  ));
test("command rejects date reversal and excessive samples", () => {
  assert.throws(() =>
    makeCommand("Earth,Venus", "2025-01-15", "2025-01-01", "6h"),
  );
  assert.throws(() =>
    makeCommand("Earth,Venus", "2000-01-01", "2040-01-01", "1h"),
  );
});
