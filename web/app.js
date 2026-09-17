import {
  MODES,
  BODIES,
  COLORS,
  AU,
  OMEGA_SUN,
  SOURCE_SURFACE_KM,
  validateBundle,
} from "./model.mjs";
import {
  newPeriod,
  requestKey,
  validatePeriod,
  validateSettings,
  screenConfig,
  runStatus,
  combinedCSV,
  isRetrieved,
  backendFor,
} from "./planner.mjs";
import { saveRun, getRun, listRuns, deleteRun } from "./history.mjs";
const $ = (id) => document.getElementById(id);
const PAGE_SIZE = 15;
let periods = [newPeriod()],
  data,
  result,
  currentRun = null,
  activePeriod = 0,
  displayBodies = [],
  page = 0;
let worker,
  pendingWorker,
  timer,
  running = false,
  controller,
  runToken = 0,
  exampleData,
  retrievalUrl = "";
function el(tag, text, className) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (className) n.className = className;
  return n;
}
function feedback(message, error = false) {
  $("feedback").textContent = message;
  $("feedback").classList.toggle("error", error);
}
function dateText(time) {
  return time.replace("T", " ").replace("Z", "").split(".")[0];
}
function colorFor(name) {
  // COLORS is parallel to BODIES, so every body has its own colour.
  const index = BODIES.indexOf(name);
  return index === -1 ? "#66776c" : COLORS[index];
}
// Event bounds are written "YYYY-MM-DD HH:MM:SS" with no zone, while samples are ISO UTC.
function eventMillis(stamp) {
  return Date.parse(stamp.replace(" ", "T") + "Z");
}
function windowsAt(time) {
  // Which screened alignment windows contain this sample, so stepping through the plot shows
  // when one window ends and another begins instead of leaving it to be inferred.
  if (!result) return [];
  const moment = Date.parse(time);
  return result.events.filter(
    (e) => eventMillis(e.start_time) <= moment && moment <= eventMillis(e.end_time),
  );
}
function stopPlay() {
  clearInterval(timer);
  timer = null;
  $("play").textContent = "▶";
  $("play").setAttribute("aria-label", "Play trajectory");
}
function settings() {
  return {
    modes: [...document.querySelectorAll("[name=mode]:checked")].map(
      (n) => n.value,
    ),
    cone: Number($("cone").value),
    tolerance: Number($("tolerance").value),
    speed: Number($("speed").value),
    latitude: $("latitude").value === "" ? null : Number($("latitude").value),
    angle: document.querySelector("[name=mode][value=arbitrary]").checked
      ? Number($("angle").value)
      : null,
  };
}
function invalidate() {
  currentRun = null;
  result = null;
  page = 0;
  stopPlay();
  $("export-csv").disabled = true;
  $("export-json").disabled = true;
  $("export-all").disabled = true;
  $("event-count").textContent = "—";
  $("run-summary").textContent =
    "Retrieve & screen to calculate these settings. Previous runs remain in History.";
  $("period-results").replaceChildren();
  $("filter").replaceChildren(new Option("All geometries", "all"));
  renderEvents();
  feedback("Configuration changed. Retrieve & screen when ready.");
}
function labelledInput(label, type, value, key, p) {
  const wrap = el("label", label);
  const input = el("input");
  input.type = type;
  input.value = value;
  input.dataset.key = key;
  input.dataset.period = p.id;
  if (type === "datetime-local") {
    input.required = true;
    input.step = "1";
  }
  wrap.append(input);
  return wrap;
}
function updatePeriodSummary(p) {
  const card = document.querySelector(`[data-card="${p.id}"]`);
  if (!card) return;
  card.querySelector(".period-summary-text").textContent =
    `${p.name || "Period " + (periods.indexOf(p) + 1)} · ${p.bodies.length} bodies`;
  card.querySelector(".period-summary-meta").textContent =
    `${p.start.slice(0, 10)} → ${p.end.slice(0, 10)} · ${p.bodies.join(" · ")}`;
}
function renderPeriods(openId = periods.at(-1)?.id) {
  $("period-count").textContent = periods.length;
  $("add-period").disabled = running || periods.length >= 8;
  $("periods").replaceChildren(
    ...periods.map((p, index) => {
      const card = el("details", undefined, "period-card");
      card.dataset.card = p.id;
      card.open = p.id === openId;
      const summary = el("summary");
      summary.append(
        el(
          "span",
          `${p.name || "Period " + (index + 1)} · ${p.bodies.length} bodies`,
          "period-summary-text",
        ),
      );
      summary.append(
        el(
          "small",
          `${p.start.slice(0, 10)} → ${p.end.slice(0, 10)} · ${p.bodies.join(" · ")}`,
          "period-summary-meta",
        ),
      );
      card.append(summary);
      const content = el("div", undefined, "period-content");
      const name = labelledInput("Period name", "text", p.name, "name", p);
      name.querySelector("input").placeholder = "Period " + (index + 1);
      name.querySelector("input").maxLength = 80;
      content.append(name);
      const sourceLabel = el("label", "Trajectory source");
      const source = el("select");
      source.dataset.key = "source";
      source.dataset.period = p.id;
      source.append(
        new Option("JPL Horizons · retrieve live", "live"),
        new Option("SPICE kernels · retrieve live", "spice"),
        new Option("SPICE where available, else Horizons", "prefer-spice"),
        new Option("Bundled January 2025 example", "example"),
        new Option("Imported trajectory file", "import"),
      );
      source.value = p.source;
      sourceLabel.append(source);
      content.append(sourceLabel);
      if (p.source === "import") {
        const file = el("input");
        file.type = "file";
        file.accept = ".json,application/json";
        file.hidden = true;
        const upload = el(
          "button",
          p.bundle ? "Replace trajectory file" : "Import trajectory JSON",
          "import-button",
        );
        upload.type = "button";
        upload.onclick = () => file.click();
        file.onchange = async () => {
          const f = file.files[0];
          if (!f) return;
          try {
            if (f.size > 20 * 1024 * 1024)
              throw Error("Use a file smaller than 20 MB.");
            const bundle = validateBundle(JSON.parse(await f.text()));
            p.bundle = bundle;
            p.cacheKey = null;
            p.bodies = Object.keys(bundle.trajectories);
            const points = Object.values(bundle.trajectories)[0];
            p.start = points[0].time;
            p.end = points.at(-1).time;
            p.fileName = f.name;
            invalidate();
            renderPeriods();
            feedback("Trajectory file loaded locally. Ready to screen.");
          } catch (error) {
            feedback("Import failed: " + error.message, true);
          }
        };
        content.append(
          file,
          upload,
          el("p", p.fileName || "Choose a file for this period.", "hint"),
        );
      }
      const dates = el("div", undefined, "field-row");
      dates.append(
        labelledInput(
          "Start · UTC",
          "datetime-local",
          p.start.replace(/Z$/, "").slice(0, 19),
          "start",
          p,
        ),
        labelledInput(
          "End · UTC",
          "datetime-local",
          p.end.replace(/Z$/, "").slice(0, 19),
          "end",
          p,
        ),
      );
      content.append(dates);
      if (isRetrieved(p.source)) {
        const spacingLabel = el("label", "Sample spacing");
        const spacing = el("select");
        spacing.dataset.period = p.id;
        spacing.dataset.key = "step";
        spacing.append(
          new Option("Every hour", "1h"),
          new Option("Every 6 hours", "6h"),
          new Option("Every day", "1d"),
        );
        spacing.value = p.step;
        spacingLabel.append(spacing);
        content.append(spacingLabel);
        if (p.cacheKey) {
          const refresh = el(
            "button",
            "Refresh trajectories on next run",
            "inline-link",
          );
          refresh.type = "button";
          refresh.onclick = () => {
            p.cacheKey = null;
            p.bundle = null;
            invalidate();
            renderPeriods();
          };
          content.append(refresh);
        }
      } else
        content.append(
          el(
            "p",
            "Uses the sample spacing and coverage recorded in the dataset.",
            "hint",
          ),
        );
      const group = el("fieldset", undefined, "body-fieldset");
      group.append(el("legend", "Spacecraft & planets"));
      // Per period, because each period carries its own body selection.
      const clearBodies = el("button", "Unselect all bodies", "inline-link");
      clearBodies.type = "button";
      clearBodies.onclick = () => {
        p.bodies = [];
        invalidate();
        renderPeriods(p.id);
        feedback(
          "All bodies unselected for this period. Choose at least two before running.",
        );
      };
      const bodyActions = el("div", undefined, "selection-actions");
      bodyActions.append(clearBodies);
      group.append(bodyActions);
      const bodyList = el("div", undefined, "body-options");
      BODIES.forEach((body) => {
        const label = el("label");
        const input = el("input");
        input.type = "checkbox";
        input.value = body;
        input.name = "body-" + p.id;
        input.dataset.period = p.id;
        input.dataset.key = "body";
        input.checked = p.bodies.includes(body);
        label.append(input, el("span", body));
        bodyList.append(label);
      });
      group.append(
        bodyList,
        el(
          "p",
          "Select at least two observing bodies. Sun adds the reference origin. Mission availability depends on the selected dates.",
          "hint",
        ),
      );
      content.append(group);
      if (periods.length > 1) {
        const remove = el("button", "Remove period", "remove-period");
        remove.type = "button";
        remove.onclick = () => {
          periods = periods.filter((x) => x.id !== p.id);
          invalidate();
          renderPeriods();
        };
        content.append(remove);
      }
      card.append(content);
      return card;
    }),
  );
}
$("periods").addEventListener("input", (event) => {
  const target = event.target;
  const p = periods.find((p) => p.id === target.dataset.period);
  if (!p) return;
  const key = target.dataset.key;
  if (key === "body")
    p.bodies = BODIES.filter((b) =>
      b === target.value ? target.checked : p.bodies.includes(b),
    );
  else if (key === "start" || key === "end")
    p[key] = target.value ? target.value + "Z" : "";
  else p[key] = target.value;
  if (key !== "name" && isRetrieved(p.source)) {
    p.cacheKey = null;
    p.bundle = null;
  }
  invalidate();
  updatePeriodSummary(p);
  if (key === "source") {
    p.bundle = null;
    p.cacheKey = null;
    renderPeriods();
  }
});
function showPeriod(index) {
  stopPlay();
  activePeriod = index;
  page = 0;
  const entry = currentRun?.periods[index];
  if (!entry) return;
  for (const [i, button] of [...$("period-results").children].entries())
    button.setAttribute("aria-pressed", String(i === index));
  result = entry.result || null;
  if (entry.bundle && entry.result) {
    // A body excluded for having no ephemeris in the window is absent from the bundle, so the
    // requested list cannot be used directly here.
    const present = entry.plan.bodies.filter((b) =>
      Object.hasOwn(entry.bundle.trajectories, b),
    );
    data = {
      ...entry.bundle,
      trajectories: Object.fromEntries(
        present.map((b) => [
          b,
          entry.bundle.trajectories[b].filter(
            (p) =>
              Date.parse(p.time) >= Date.parse(entry.plan.start) &&
              Date.parse(p.time) <= Date.parse(entry.plan.end),
          ),
        ]),
      ),
    };
    displayBodies = present;
    setupPlot();
  } else {
    data = null;
    displayBodies = [];
    $("orbit").replaceChildren(
      el(
        "div",
        "No plot for this period. See the error in its screening results.",
        "empty",
      ),
    );
    $("legend").replaceChildren();
    $("active-windows").replaceChildren();
    $("play").disabled = true;
    $("time-slider").disabled = true;
    $("sample-date").textContent = "—";
    $("range-start").textContent = "—";
    $("range-end").textContent = "—";
    $("sample-number").textContent = "—";
  }
  $("source-note").textContent =
    `${entry.label} · ${entry.plan.bodies.join(" + ")} · ${entry.plan.source === "live" ? "JPL Horizons" : entry.plan.source === "spice" ? "SPICE kernels" : entry.plan.source === "prefer-spice" ? "SPICE where available" : entry.plan.source === "example" ? "Bundled example" : "Imported data"}${entry.cached ? " · reused retrieved data" : ""}`;
  $("event-count").textContent = result ? result.events.length : "—";
  $("export-csv").disabled = !result;
  $("export-json").disabled = !result;
  $("export-all").disabled = !currentRun.periods.some((p) => p.result);
  $("run-summary").textContent = result
    ? `${entry.plan.start.slice(0, 10)} → ${entry.plan.end.slice(0, 10)} · ${result.metadata.sample_count_per_body} samples/body · ${currentRun.settings.modes.map((m) => MODES[m]).join(", ")}`
    : entry.error || "No result for this period.";
  $("filter").replaceChildren(
    new Option("All geometries", "all"),
    ...currentRun.settings.modes.map((m) => new Option(MODES[m], m)),
  );
  renderEvents();
}
function showRun(record) {
  currentRun = record;
  $("period-results").replaceChildren(
    ...record.periods.map((p, i) => {
      const button = el(
        "button",
        `${p.label} · ${p.result ? p.result.events.length + " windows" : p.status}`,
      );
      button.setAttribute("aria-pressed", String(i === 0));
      button.onclick = () => showPeriod(i);
      return button;
    }),
  );
  showPeriod(0);
}
// Bodies need not cover the same interval, because a mission's ephemeris can begin or end
// inside the window. The scrubber therefore walks the union of every body's sample times
// rather than one body's array, which no body is guaranteed to span.
function timeline() {
  return [
    ...new Set(
      Object.values(data.trajectories).flatMap((points) =>
        points.map((p) => p.time),
      ),
    ),
  ].sort();
}
function setupPlot() {
  const times = timeline();
  $("time-slider").disabled = false;
  $("play").disabled = false;
  $("time-slider").max = Math.max(0, times.length - 1);
  $("time-slider").value = 0;
  $("range-start").textContent = dateText(times[0]);
  $("range-end").textContent = dateText(times.at(-1));
  draw();
}
function svgNode(tag, attrs, text) {
  const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  if (text !== undefined) n.textContent = text;
  return n;
}
function draw() {
  if (!data) return;
  const allNames = Object.keys(data.trajectories),
    times = timeline(),
    index = Math.min(Number($("time-slider").value), times.length - 1);
  const time = times[index];
  // Matched by timestamp, so a body sampled only over part of the window is drawn where it
  // actually is. Indexing every body by the same array position put truncated bodies at the
  // wrong epoch, and ran off the end of the shorter ones.
  const sampleAt = new Map(
    Object.entries(data.trajectories).map(([name, points]) => [
      name,
      points.find((p) => p.time === time),
    ]),
  );
  const names = displayBodies.filter((name) => sampleAt.get(name));
  const absent = displayBodies.filter((name) => !sampleAt.get(name));
  $("sample-date").textContent = dateText(time) + " UTC";
  $("sample-number").textContent = `${index + 1} / ${times.length}`;
  const windows = windowsAt(time);
  renderActiveWindows(windows, absent);
  // Drawn only where a Parker window is actually open, and only for the bodies that window
  // matched, so the spiral shows why those bodies are connected at this sample rather than
  // decorating every body for the whole run.
  const parkerBodies = new Set(
    windows
      .filter((e) => e.geometry === "parker" || e.geometry === "coneparker")
      .flatMap((e) => e.bodies.split(";")),
  );
  const spiralSpeed = parkerBodies.size ? currentRun.settings.speed : null;
  // The note stays visible so the convention is always documented; it reports the speed the
  // run was screened with, falling back to the value currently in the form.
  const notedSpeed =
    spiralSpeed ??
    currentRun?.settings?.speed ??
    (Number($("speed").value) || 400);
  $("spiral-speed").textContent = `${notedSpeed} km/s`;
  const svg = svgNode("svg", {
    viewBox: "0 0 480 390",
    role: "img",
    "aria-label": `Heliocentric positions at ${dateText(time)} UTC. ${names.join(", ")}.`,
  });
  svg.append(
    svgNode("title", {}, "HCI trajectory projection"),
    svgNode(
      "desc",
      {},
      "Concentric distance guides in AU; positions are projected into the solar equatorial plane.",
    ),
  );
  const cx = 235,
    cy = 192,
    r = 157;
  const maxAU =
    names.reduce(
      (largest, name) =>
        data.trajectories[name].reduce(
          (m, p) => Math.max(m, p.radius_km / AU),
          largest,
        ),
      0.25,
    ) * 1.12;
  const scale = r / maxAU;
  const position = (p) => {
    const distance = (p.radius_km / AU) * Math.cos((p.lat_deg * Math.PI) / 180);
    return [
      cx + distance * scale * Math.cos((p.lon_deg * Math.PI) / 180),
      cy - distance * scale * Math.sin((p.lon_deg * Math.PI) / 180),
    ];
  };
  for (let k = 1; k <= 4; k++) {
    const radius = (r * k) / 4;
    svg.append(
      svgNode("circle", {
        cx,
        cy,
        r: radius,
        fill: "none",
        stroke: "#e4e9df",
        "stroke-dasharray": k === 4 ? "none" : "3 5",
      }),
    );
    svg.append(
      svgNode(
        "text",
        { x: cx + 5, y: cy - radius - 5, fill: "#94a18e", "font-size": 8 },
        ((maxAU * k) / 4).toFixed(2) + " AU",
      ),
    );
  }
  for (let deg = 0; deg < 360; deg += 45) {
    const angle = (deg * Math.PI) / 180;
    svg.append(
      svgNode("line", {
        x1: cx,
        y1: cy,
        x2: cx + r * Math.cos(angle),
        y2: cy - r * Math.sin(angle),
        stroke: "#edf0e8",
      }),
    );
    svg.append(
      svgNode(
        "text",
        {
          x: cx + (r + 17) * Math.cos(angle),
          y: cy - (r + 17) * Math.sin(angle) + 3,
          "text-anchor": "middle",
          fill: "#91a088",
          "font-size": 9,
        },
        deg + "°",
      ),
    );
  }
  const labels = [];
  names.forEach((name) => {
    const color = colorFor(name);
    const trajectory = data.trajectories[name];
    svg.append(
      svgNode("polyline", {
        points: trajectory
          .filter(
            (_, i) =>
              i % Math.max(1, Math.ceil(trajectory.length / 1000)) === 0 ||
              i === trajectory.length - 1,
          )
          .map((p) => position(p).join(","))
          .join(" "),
        fill: "none",
        stroke: color,
        "stroke-width": 1.8,
        opacity: 0.45,
      }),
    );
    const here = sampleAt.get(name);
    if (spiralSpeed && parkerBodies.has(name))
      svg.append(parkerSpiral(here, color, position, spiralSpeed));
    const [x, y] = position(here);
    labels.push({ name, x, y, color });
    svg.append(
      svgNode("line", {
        x1: cx,
        y1: cy,
        x2: x,
        y2: y,
        stroke: color,
        opacity: 0.32,
        "stroke-dasharray": "3 4",
      }),
    );
    svg.append(
      svgNode("circle", { cx: x, cy: y, r: 9, fill: color, opacity: 0.12 }),
      svgNode("circle", {
        cx: x,
        cy: y,
        r: 4,
        fill: color,
        stroke: "white",
        "stroke-width": 1.5,
      }),
    );
  });
  svg.append(
    svgNode("circle", { cx, cy, r: 17, fill: "#edc66d", opacity: 0.1 }),
    svgNode("circle", { cx, cy, r: 10, fill: "#edc66d", opacity: 0.25 }),
    svgNode("circle", { cx, cy, r: 5, fill: "#d8ab50" }),
  );
  svg.append(
    svgNode(
      "text",
      {
        x: 235,
        y: 385,
        "text-anchor": "middle",
        fill: "#84917d",
        "font-size": 9,
      },
      dateText(time) + " UTC",
    ),
  );
  for (const side of [-1, 1]) {
    const items = labels
      .filter((p) => (p.x < cx ? -1 : 1) === side)
      .sort((a, b) => a.y - b.y);
    let bottom = 26;
    items.forEach((p, i) => {
      const labelY = Math.min(
        352 - (items.length - i - 1) * 17,
        Math.max(bottom, p.y),
      );
      bottom = labelY + 17;
      const labelX =
        side > 0
          ? Math.min(370, Math.max(270, p.x + 12))
          : Math.max(108, Math.min(200, p.x - 12));
      svg.append(
        svgNode("line", {
          x1: p.x,
          y1: p.y,
          x2: labelX,
          y2: labelY,
          stroke: p.color,
          opacity: 0.6,
          "stroke-width": 0.7,
        }),
      );
      svg.append(
        svgNode(
          "text",
          {
            x: labelX + (side > 0 ? 3 : -3),
            y: labelY + 3,
            "text-anchor": side > 0 ? "start" : "end",
            fill: p.color,
            "font-size": 10,
            "font-weight": 600,
            stroke: "white",
            "stroke-width": 3,
            "paint-order": "stroke",
          },
          p.name,
        ),
      );
    });
  }
  $("orbit").replaceChildren(svg);
  $("legend").replaceChildren(
    ...displayBodies.map((name) => {
      const p = sampleAt.get(name);
      const row = el("div", undefined, "legend-entry");
      const dot = el("span", undefined, "legend-dot");
      dot.style.background = colorFor(name);
      const info = el("span", name);
      info.append(
        el(
          "small",
          p
            ? `${(p.radius_km / AU).toFixed(3)} AU · ${p.lon_deg.toFixed(1)}° lon · ${p.lat_deg.toFixed(1)}° lat`
            : "outside its ephemeris coverage at this sample",
        ),
      );
      if (!p) row.classList.add("absent");
      row.append(dot, info);
      return row;
    }),
  );
}
function parkerSpiral(sample, color, position, speedKmS) {
  // The ballistic spiral through this body: a parcel now at radius r left the source surface
  // when the footpoint was Omega*(r_body - r)/u_sw ahead in longitude, which is the same
  // mapping check_geometry uses, read outward instead of back to the footpoint. The speed is
  // the one the run was screened with, not the current form value, which may have moved on.
  const points = [];
  const steps = 60;
  for (let i = 0; i <= steps; i++) {
    const radius =
      SOURCE_SURFACE_KM +
      ((sample.radius_km - SOURCE_SURFACE_KM) * i) / steps;
    // Radius in km over speed in km/s gives the travel time in seconds; mixing km with m/s
    // here would wind the spiral a thousand times too tightly.
    const lead =
      ((OMEGA_SUN * (sample.radius_km - radius)) / speedKmS) * (180 / Math.PI);
    points.push(
      position({
        radius_km: radius,
        lat_deg: sample.lat_deg,
        lon_deg: sample.lon_deg + lead,
      }).join(","),
    );
  }
  return svgNode("polyline", {
    points: points.join(" "),
    fill: "none",
    stroke: color,
    "stroke-width": 1.2,
    "stroke-dasharray": "1 3",
    opacity: 0.75,
  });
}
function renderActiveWindows(windows, absent) {
  const holder = $("active-windows");
  holder.replaceChildren();
  const plain = (text, cls) => {
    const tag = el("span", undefined, cls);
    tag.append(el("strong", text));
    return tag;
  };
  if (absent.length)
    holder.append(
      plain(`${absent.join(", ")}: no ephemeris here`, "window-tag absent"),
    );
  if (!windows.length) {
    holder.append(
      plain(
        result ? "No alignment at this sample" : "Screen a run to see alignments",
        "window-tag none",
      ),
    );
    return;
  }
  for (const e of windows) {
    const tag = el("span", undefined, "window-tag");
    tag.append(
      el("strong", MODES[e.geometry] || e.geometry),
      el("small", e.bodies.split(";").join(" + ")),
    );
    tag.title = `${MODES[e.geometry] || e.geometry}: ${e.start_time} → ${e.end_time}`;
    holder.append(tag);
  }
}
function renderEvents() {
  const holder = $("event-table");
  holder.replaceChildren();
  if (!result) {
    holder.append(
      el("div", "Your alignment windows will appear here.", "empty"),
    );
    $("filter-count").textContent = "";
    $("pagination").hidden = true;
    return;
  }
  const filtered = result.events.filter(
    (e) => $("filter").value === "all" || e.geometry === $("filter").value,
  );
  $("filter-count").textContent =
    `${filtered.length} window${filtered.length === 1 ? "" : "s"}`;
  if (!filtered.length) {
    holder.append(
      el(
        "div",
        result.events.length
          ? "No windows for this geometry. Try another filter."
          : "No alignments found for these settings. Try a wider tolerance or another geometry.",
        "empty",
      ),
    );
    $("pagination").hidden = true;
    return;
  }
  const table = el("table");
  table.append(el("caption", "Candidate alignment windows, UTC", "sr-only"));
  const head = el("thead"),
    tr = el("tr");
  ["Geometry", "Bodies", "Start / end · UTC", "Duration", "View"].forEach(
    (t) => {
      const th = el("th", t);
      th.scope = "col";
      tr.append(th);
    },
  );
  head.append(tr);
  table.append(head);
  const body = el("tbody");
  filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).forEach((e) => {
    const row = el("tr"),
      geometry = el("td");
    geometry.append(el("span", MODES[e.geometry], "geometry-tag"));
    const times = el("td");
    times.append(el("div", e.start_time), el("div", e.end_time, "hint"));
    const jump = el("button", "↗", "jump");
    jump.setAttribute(
      "aria-label",
      `View ${MODES[e.geometry]} window starting ${e.start_time}`,
    );
    jump.addEventListener("click", () => {
      stopPlay();
      const index = timeline().findIndex(
        (t) => Date.parse(t) >= eventMillis(e.start_time),
      );
      $("time-slider").value = Math.max(0, index);
      draw();
      $("orbit-title").scrollIntoView({ block: "center", behavior: "instant" });
    });
    const action = el("td");
    action.append(jump);
    row.append(
      geometry,
      el("td", e.bodies.split(";").join(" + ")),
      times,
      el(
        "td",
        Number(e.duration_hours).toLocaleString(undefined, {
          maximumFractionDigits: 2,
        }) + " h",
      ),
      action,
    );
    body.append(row);
  });
  table.append(body);
  holder.append(table);
  $("pagination").hidden = filtered.length <= PAGE_SIZE;
  $("prev").disabled = page === 0;
  $("next").disabled = (page + 1) * PAGE_SIZE >= filtered.length;
  $("page-label").textContent =
    `Page ${page + 1} of ${Math.ceil(filtered.length / PAGE_SIZE)}`;
}
function busy(value) {
  running = value;
  for (const item of $("screen-form").elements) item.disabled = value;
  $("cancel").disabled = false;
  $("cancel").hidden = !value;
  $("run").textContent = value
    ? "Retrieving & screening…"
    : "Retrieve & screen →";
  if (!value) {
    $("angle").disabled = $("angle-label").hidden;
    $("add-period").disabled = periods.length >= 8;
  }
}
function warmEngine() {
  // Started at page load so the Python runtime downloads while the form is being filled in.
  // Screening itself takes milliseconds; without this the whole runtime fetch sat in the
  // critical path, beginning only once the first retrieval had already finished.
  try {
    if (!worker) worker = new Worker("./worker.js");
    worker.onmessage = () => {};
    worker.postMessage({ warm: true });
  } catch {
    // An unavailable worker is reported when a screening is actually requested.
  }
}
function screen(payload, config, signal) {
  return new Promise((resolve, reject) => {
    if (!worker) worker = new Worker("./worker.js");
    const timer = setTimeout(() => {
      worker?.terminate();
      worker = null;
      finish(Error("Screening timed out. Try a smaller dataset."));
    }, 120000);
    const abort = () => {
      worker?.terminate();
      worker = null;
      finish(new DOMException("Cancelled", "AbortError"));
    };
    function finish(error, value) {
      clearTimeout(timer);
      signal.removeEventListener("abort", abort);
      pendingWorker = null;
      error ? reject(error) : resolve(value);
    }
    pendingWorker = { reject: abort };
    signal.addEventListener("abort", abort, { once: true });
    worker.onmessage = ({ data: reply }) => {
      if (reply.type === "status") {
        feedback(reply.message);
        return;
      }
      // A warm-up acknowledgement can still be in flight when a run starts, and must not be
      // mistaken for a result: falling through would resolve the run with no events.
      if (reply.type === "warm") return;
      if (reply.type === "error") finish(Error(reply.message));
      else finish(null, reply.result);
    };
    worker.onerror = () => {
      worker?.terminate();
      worker = null;
      finish(Error("The Python engine could not start. Try again."));
    };
    if (signal.aborted) {
      abort();
      return;
    }
    worker.postMessage({ payload, config });
  });
}
async function obtain(p, signal) {
  if (p.source === "example")
    return { bundle: structuredClone(exampleData), cached: true };
  if (p.source === "import") {
    if (!p.bundle) throw Error("Import a trajectory file for this period.");
    return { bundle: structuredClone(p.bundle), cached: true };
  }
  if (p.bundle && p.cacheKey === requestKey(p))
    return { bundle: structuredClone(p.bundle), cached: true };
  if (!retrievalUrl)
    throw Error(
      "Live retrieval is not connected on this deployment. The site owner needs to connect the SolarConflux retrieval service.",
    );
  const timeout = AbortSignal.timeout(240000);
  const combined = AbortSignal.any([signal, timeout]);
  let response;
  try {
    response = await fetch(retrievalUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bodies: p.bodies,
        start: p.start,
        end: p.end,
        step: p.step,
        source: backendFor(p.source),
      }),
      signal: combined,
    });
  } catch (error) {
    if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
    if (timeout.aborted)
      throw Error("Retrieval timed out. Try a shorter period later.");
    throw Error(
      "Could not reach the retrieval service. Check your connection and try again.",
    );
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw Error("The retrieval service returned an unexpected response.");
  }
  if (!response.ok)
    throw Error(payload.error || "Horizons retrieval failed. Try again later.");
  validateBundle(payload);
  return { bundle: payload, cached: false };
}
async function hashBundle(bundle) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify(bundle)),
  );
  return Array.from(new Uint8Array(digest), (x) =>
    x.toString(16).padStart(2, "0"),
  ).join("");
}
function syncPeriods() {
  // Read native controls at submission as well as on input; date controls can
  // commit on change rather than input on some browsers.
  for (const p of periods) {
    const card = document.querySelector(`[data-card="${p.id}"]`);
    if (!card) continue;
    for (const input of card.querySelectorAll("[data-key]")) {
      const key = input.dataset.key;
      if (key === "body") continue;
      p[key] = ["start", "end"].includes(key)
        ? input.value
          ? input.value + "Z"
          : ""
        : input.value;
    }
    p.bodies = [...card.querySelectorAll('[data-key="body"]:checked')].map(
      (input) => input.value,
    );
  }
}
async function run(event) {
  event?.preventDefault();
  if (running) return;
  let options;
  try {
    syncPeriods();
    options = validateSettings(settings());
    periods.forEach((p, i) => {
      try {
        validatePeriod(p);
      } catch (e) {
        throw Error(`Period ${i + 1}: ${e.message}`);
      }
    });
    if (
      !retrievalUrl &&
      periods.some(
        (p) =>
          isRetrieved(p.source) && !(p.bundle && p.cacheKey === requestKey(p)),
      )
    )
      throw Error(
        "Live trajectories are unavailable: this website has no retrieval service connected. Use the bundled example or import a trajectory file until the service is connected.",
      );
  } catch (error) {
    feedback(error.message, true);
    return;
  }
  stopPlay();
  controller = new AbortController();
  const signal = controller.signal;
  const token = ++runToken;
  const record = {
    schema: "solarconflux.run.v1",
    id: crypto.randomUUID(),
    title: $("run-title").value.trim() || "Untitled run",
    createdAt: new Date().toISOString(),
    settings: structuredClone(options),
    status: "running",
    periods: periods.map((p, i) => ({
      plan: { ...structuredClone(p), bundle: undefined, cacheKey: undefined },
      label: p.name.trim() || "Period " + (i + 1),
      status: "pending",
      result: null,
      bundle: null,
    })),
  };
  currentRun = null;
  result = null;
  $("export-csv").disabled = true;
  $("export-json").disabled = true;
  $("export-all").disabled = true;
  $("event-count").textContent = "—";
  $("period-results").replaceChildren();
  renderEvents();
  // Disabling the form is paired with the finally below. Anything that can throw must stay
  // outside that pair, or a failure here would leave every control -- including Add period
  // -- disabled until the page is reloaded.
  busy(true);
  try {
    for (let i = 0; i < periods.length; i++) {
      const p = periods[i],
        entry = record.periods[i];
      if (signal.aborted) {
        entry.status = "cancelled";
        entry.error = "Cancelled before this period completed.";
        continue;
      }
      try {
        feedback(`${entry.label}: retrieving ${p.bodies.join(", ")}…`);
        const obtained = await obtain(p, signal);
        if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
        entry.bundle = obtained.bundle;
        entry.cached = obtained.cached;
        entry.coverageNotes = obtained.bundle.coverage_notes || null;
        p.bundle = obtained.bundle;
        if (isRetrieved(p.source)) p.cacheKey = requestKey(p);
        const c = screenConfig(p, options, entry.bundle);
        feedback(`${entry.label}: screening ${p.bodies.length} bodies…`);
        entry.result = await screen(entry.bundle, c, signal);
        entry.result.metadata.dataset_sha256 = await hashBundle(entry.bundle);
        entry.result.metadata.dataset_hash_encoding =
          "SHA-256 of UTF-8 JSON.stringify(bundle)";
        entry.result.metadata.period_id = p.id;
        entry.result.metadata.period_name = entry.label;
        entry.status = "complete";
      } catch (error) {
        entry.status = signal.aborted ? "cancelled" : "failed";
        entry.error = error.message;
      }
    }
    record.status = runStatus(record.periods);
    let saved = true;
    try {
      await saveRun(record);
    } catch {
      saved = false;
    }
    if (token !== runToken) return;
    showRun(record);
    await refreshHistoryCount();
    const count = record.periods.filter((p) => p.status === "complete").length;
    const errors = record.periods
      .filter((p) => p.error)
      .map((p) => `${p.label}: ${p.error}`)
      .join(" ");
    // Truncated or excluded bodies must be stated, never silently dropped.
    const coverage = record.periods
      .filter((p) => p.coverageNotes)
      .flatMap((p) =>
        Object.entries(p.coverageNotes).map(
          ([body, note]) => `${p.label}: ${body} ${note}`,
        ),
      )
      .join(" ");
    feedback(
      `${count} of ${record.periods.length} periods completed. ${errors ? errors + " " : ""}${coverage ? coverage + " " : ""}${saved ? "Run record saved in History." : "History could not be saved; download the available results to keep them."}`,
      !saved || record.status === "failed",
    );
  } finally {
    busy(false);
    controller = null;
    renderPeriods(null);
    // Cancelling or timing out terminates the worker, discarding the interpreter. Rebuild it
    // now, while nothing is in flight, so the next run does not pay initialisation again.
    if (!worker) warmEngine();
  }
}
async function refreshHistoryCount() {
  try {
    $("history-count").textContent = (await listRuns()).length || "";
  } catch {
    $("history-count").textContent = "";
  }
}
async function renderHistory() {
  const holder = $("history-list");
  holder.replaceChildren(el("p", "Loading saved runs…", "empty"));
  try {
    const runs = await listRuns();
    $("history-count").textContent = runs.length || "";
    holder.replaceChildren();
    if (!runs.length) {
      holder.append(
        el(
          "div",
          "No saved runs yet. Retrieve and screen a period in the Explorer to start your history.",
          "empty",
        ),
      );
      return;
    }
    runs.forEach((r) => {
      const card = el("article", undefined, "panel history-card");
      const heading = el("div", undefined, "history-card-heading");
      const title = el("div");
      title.append(
        el("h2", r.title),
        el("p", dateText(r.createdAt) + " UTC", "hint"),
      );
      heading.append(title, el("span", r.status, "small-pill"));
      card.append(heading);
      r.periods.forEach((p, i) =>
        card.append(
          el(
            "p",
            `Period ${i + 1} · ${p.start.slice(0, 10)} → ${p.end.slice(0, 10)} · ${p.bodies.join(" + ")} · ${p.status === "complete" ? p.events + " windows" : p.status}`,
            "history-period",
          ),
        ),
      );
      card.append(el("p", r.modes.map((m) => MODES[m]).join(" · "), "hint"));
      const actions = el("div", undefined, "history-actions");
      const open = el("button", "Open run", "primary");
      open.onclick = async () => {
        try {
          const full = await getRun(r.id);
          if (!full) throw Error("This run is no longer available.");
          restoreRun(full);
          location.hash = "explorer";
        } catch (e) {
          $("history-feedback").textContent = e.message;
        }
      };
      const backup = el("button", "Download run");
      backup.onclick = async () => {
        try {
          const full = await getRun(r.id);
          download(
            JSON.stringify(full, null, 2),
            "solarconflux_run_" + r.id + ".json",
            "application/json",
          );
        } catch {
          $("history-feedback").textContent = "Could not download this run.";
        }
      };
      const remove = el("button", "Delete");
      remove.onclick = async () => {
        try {
          const deleted = await getRun(r.id);
          await deleteRun(r.id);
          await renderHistory();
          $("history-feedback").replaceChildren(el("span", "Run deleted. "));
          const undo = el("button", "Undo");
          undo.onclick = async () => {
            try {
              await saveRun(deleted);
              $("history-feedback").textContent = "Run restored.";
              await renderHistory();
            } catch {
              $("history-feedback").textContent = "Could not restore this run.";
            }
          };
          $("history-feedback").append(undo);
        } catch {
          $("history-feedback").textContent = "Could not delete this run.";
        }
      };
      actions.append(open, backup, remove);
      card.append(actions);
      holder.append(card);
    });
  } catch {
    $("history-list").replaceChildren(
      el(
        "div",
        "History is unavailable in this browser. You can still screen and download results.",
        "empty",
      ),
    );
  }
}
function restoreRun(full) {
  if (running) {
    feedback(
      "Wait for the current run to finish before opening history.",
      true,
    );
    return;
  }
  $("run-title").value = full.title;
  for (const input of document.querySelectorAll("[name=mode]"))
    input.checked = full.settings.modes.includes(input.value);
  for (const id of ["cone", "tolerance", "speed", "latitude", "angle"])
    $(id).value = full.settings[id] ?? "";
  $("angle-label").hidden = !full.settings.modes.includes("arbitrary");
  $("angle").disabled = $("angle-label").hidden;
  periods = full.periods.map((e) => ({
    ...structuredClone(e.plan),
    bundle: structuredClone(e.bundle),
    cacheKey: isRetrieved(e.plan.source) && e.bundle ? requestKey(e.plan) : null,
  }));
  renderPeriods(null);
  showRun(full);
  feedback(
    "Saved run reopened. Results and trajectories are restored without a network request.",
  );
}
function route() {
  const history = location.hash === "#history";
  $("history-page").hidden = !history;
  $("explorer-page").hidden = history;
  document.querySelector(".heading").hidden = history;
  for (const [id, active] of [
    ["history-link", history],
    ["explorer-link", !history],
  ]) {
    if (active) $(id).setAttribute("aria-current", "page");
    else $(id).removeAttribute("aria-current");
  }
  document.title = history
    ? "Run history · SolarConflux"
    : "SolarConflux · Alignment explorer";
  if (history) {
    stopPlay();
    renderHistory();
  }
}
function download(content, name, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = el("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("screen-form").addEventListener("submit", run);
$("screen-form").addEventListener("input", (event) => {
  if (event.target.closest("#periods")) return;
  invalidate();
  $("angle-label").hidden = !document.querySelector(
    "[name=mode][value=arbitrary]",
  ).checked;
  $("angle").disabled = $("angle-label").hidden;
});
$("unselect-geometries").onclick = () => {
  document.querySelectorAll("[name=mode]").forEach((c) => (c.checked = false));
  $("angle-label").hidden = true;
  $("angle").disabled = true;
  invalidate();
  feedback("All geometries unselected. Choose at least one before running.");
};
$("add-period").onclick = () => {
  periods.push(newPeriod(periods.at(-1)));
  invalidate();
  renderPeriods();
};
$("cancel").onclick = () => {
  controller?.abort();
  feedback("Cancelling. Completed periods will remain in History.");
};
$("time-slider").addEventListener("input", () => {
  stopPlay();
  draw();
});
$("play").onclick = () => {
  if (timer) {
    stopPlay();
    return;
  }
  if (!data) return;
  $("play").textContent = "Ⅱ";
  $("play").setAttribute("aria-label", "Pause trajectory");
  timer = setInterval(() => {
    $("time-slider").value =
      (Number($("time-slider").value) + 1) % (Number($("time-slider").max) + 1);
    draw();
  }, 350);
};
$("filter").onchange = () => {
  page = 0;
  renderEvents();
};
$("prev").onclick = () => {
  page--;
  renderEvents();
};
$("next").onclick = () => {
  page++;
  renderEvents();
};
$("export-csv").onclick = () => {
  if (result)
    download(
      result.csv,
      "solarconflux_period_" + (activePeriod + 1) + ".csv",
      "text/csv",
    );
};
$("export-json").onclick = () => {
  if (result)
    download(
      JSON.stringify(result.metadata, null, 2),
      "run_metadata_period_" + (activePeriod + 1) + ".json",
      "application/json",
    );
};
$("export-all").onclick = () => {
  if (currentRun)
    download(
      combinedCSV(currentRun.periods),
      "solarconflux_all_periods.csv",
      "text/csv",
    );
};
for (const id of ["method-button", "method-inline"])
  $(id).onclick = () => $("method-dialog").showModal();
document
  .querySelectorAll("[data-close]")
  .forEach((b) => (b.onclick = () => b.closest("dialog").close()));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopPlay();
});
window.addEventListener("hashchange", route);
async function start() {
  renderPeriods();
  renderEvents();
  route();
  await refreshHistoryCount();
  try {
    const configResponse = await fetch("./config.json");
    if (configResponse.ok) {
      const config = await configResponse.json();
      if (config.retrievalUrl) {
        const endpoint = new URL(config.retrievalUrl);
        if (
          endpoint.protocol !== "https:" &&
          !(
            endpoint.protocol === "http:" &&
            ["localhost", "127.0.0.1"].includes(endpoint.hostname)
          )
        )
          throw Error("The retrieval service must use HTTPS.");
        retrievalUrl = endpoint.href;
      }
    }
  } catch {
    feedback("Could not load the retrieval connection settings.", true);
  }
  if (!retrievalUrl && ["localhost", "127.0.0.1"].includes(location.hostname))
    retrievalUrl = new URL("/api/trajectories", location.origin).href;
  try {
    const response = await fetch("./example.json");
    if (!response.ok) throw Error("Example could not be loaded.");
    exampleData = validateBundle(await response.json());
    data = exampleData;
    displayBodies = Object.keys(data.trajectories);
    setupPlot();
    feedback(
      retrievalUrl
        ? "Ready. Select periods and bodies, then retrieve & screen."
        : "Live trajectories are unavailable: no retrieval service is connected. You can screen the bundled example or import a trajectory file.",
      !retrievalUrl,
    );
  } catch (error) {
    feedback(error.message, true);
  }
}
start();
warmEngine();
