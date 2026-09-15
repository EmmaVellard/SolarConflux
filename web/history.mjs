// Store complete run snapshots, including trajectories, for offline reopening.
const DB_NAME = "solarconflux-history";
let database;
function openDatabase() {
  if (!database)
    database = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () =>
        request.result.createObjectStore("runs", { keyPath: "id" });
      request.onsuccess = () => {
        request.result.onversionchange = () => {
          request.result.close();
          database = null;
        };
        resolve(request.result);
      };
      request.onerror = () => reject(request.error);
      request.onblocked = () =>
        reject(Error("Close other SolarConflux tabs to open history."));
    }).catch((error) => {
      database = null;
      throw error;
    });
  return database;
}
async function transaction(mode, action) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("runs", mode);
    let value;
    const request = action(tx.objectStore("runs"));
    if (request)
      request.onsuccess = () => {
        value = request.result;
      };
    tx.oncomplete = () => resolve(value);
    tx.onerror = () => reject(tx.error || Error("History could not be saved."));
    tx.onabort = () =>
      reject(tx.error || Error("History transaction was interrupted."));
  });
}
export function saveRun(run) {
  return transaction("readwrite", (store) => store.put(structuredClone(run)));
}
export function getRun(id) {
  return transaction("readonly", (store) => store.get(id));
}
export function deleteRun(id) {
  return transaction("readwrite", (store) => store.delete(id));
}
export async function listRuns() {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const summaries = [];
    const tx = db.transaction("runs", "readonly");
    const request = tx.objectStore("runs").openCursor();
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return;
      const r = cursor.value;
      summaries.push({
        id: r.id,
        title: r.title,
        createdAt: r.createdAt,
        status: r.status,
        periods: r.periods.map((p) => ({
          start: p.plan.start,
          end: p.plan.end,
          bodies: p.plan.bodies,
          status: p.status,
          events: p.result?.events.length || 0,
        })),
        modes: r.settings.modes,
      });
      cursor.continue();
    };
    tx.oncomplete = () =>
      resolve(summaries.sort((a, b) => b.createdAt.localeCompare(a.createdAt)));
    tx.onerror = () => reject(tx.error);
  });
}
