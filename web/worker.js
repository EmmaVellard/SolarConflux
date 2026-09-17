// The Python source is packaged from this checkout, never reimplemented in JavaScript.
let runtime;
async function getRuntime() {
  if (!runtime)
    runtime = (async () => {
      self.postMessage({
        type: "status",
        message: "Loading the Python engine… First use may take a moment.",
      });
      importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js");
      const py = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/",
      });
      const [response, manifestResponse] = await Promise.all([
        fetch("./engine.zip"),
        fetch("./engine-manifest.json"),
      ]);
      if (!response.ok || !manifestResponse.ok)
        throw Error(
          "The Python engine files could not be loaded. Reload and try again.",
        );
      const bytes = await response.arrayBuffer();
      const manifest = await manifestResponse.json();
      const digest = Array.from(
        new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
        (x) => x.toString(16).padStart(2, "0"),
      ).join("");
      if (digest !== manifest.sha256)
        throw Error(
          "Engine integrity check failed. Reload to get a consistent build.",
        );
      py.unpackArchive(bytes, "zip");
      await py.runPythonAsync(
        "import json\nfrom solarconflux.browser import screen_bundle, load_bundle",
      );
      return py;
    })();
  try {
    return await runtime;
  } catch (error) {
    runtime = null;
    throw error;
  }
}
self.onmessage = async ({ data }) => {
  // Warming only primes the interpreter. getRuntime memoises it, so fetching the ~20 MB
  // Pyodide runtime overlaps with the user filling in the form rather than landing in the
  // critical path after they press Run. A failure here is deliberately swallowed: the real
  // screening call retries and reports properly.
  if (data.warm) {
    try {
      await getRuntime();
    } catch {}
    self.postMessage({ type: "warm" });
    return;
  }
  try {
    const py = await getRuntime();
    py.globals.set("payload_json", JSON.stringify(data.payload));
    py.globals.set("config_json", JSON.stringify(data.config));
    self.postMessage({
      type: "status",
      message: "Screening trajectory samples…",
    });
    const result = await py.runPythonAsync(
      "json.dumps(screen_bundle(json.loads(payload_json), json.loads(config_json)), allow_nan=False)",
    );
    self.postMessage({ type: "result", result: JSON.parse(result) });
  } catch (error) {
    self.postMessage({
      type: "error",
      message: String(error.message || error)
        .split("\n")
        .filter(Boolean)
        .slice(-1)[0],
    });
  }
};
