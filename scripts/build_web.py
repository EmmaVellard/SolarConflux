"""Build the static screening GUI; live retrieval uses a separate Python service."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist"
if DEST.exists():
    shutil.rmtree(DEST)
shutil.copytree(ROOT / "web", DEST)
with zipfile.ZipFile(DEST / "engine.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((ROOT / "solarconflux").glob("*.py")):
        archive.write(path, path.relative_to(ROOT))
(DEST / "engine-manifest.json").write_text(json.dumps({"sha256": hashlib.sha256((DEST / "engine.zip").read_bytes()).hexdigest()}))
config = json.loads((ROOT / "web" / "config.json").read_text())
config["retrievalUrl"] = os.environ.get("SOLARCONFLUX_API_URL") or config.get("retrievalUrl", "")
(DEST / "config.json").write_text(json.dumps(config))

def digest(name):
    return hashlib.sha256((DEST / name).read_bytes()).hexdigest()[:12]


def stamp(name, versions):
    """Point one file's runtime references at the versioned URLs of its dependencies."""
    text = (DEST / name).read_text()
    for asset, version in versions.items():
        text = text.replace(f'"./{asset}"', f'"./{asset}?v={version}"')
    (DEST / name).write_text(text)


# Only index.html's own assets used to be versioned, so a released app.js could import a
# browser-cached model.mjs from an earlier build. A module missing a name the new app.js
# imports fails at link time, which silently leaves the whole page without event handlers.
# Dependencies are therefore stamped leaf first, so every reference carries its target's hash.
stamp("worker.js", {"engine.zip": digest("engine.zip"),
                    "engine-manifest.json": digest("engine-manifest.json")})
leaves = {"model.mjs": digest("model.mjs"), "history.mjs": digest("history.mjs")}
stamp("planner.mjs", leaves)
stamp("app.js", {**leaves,
                 "planner.mjs": digest("planner.mjs"),
                 "worker.js": digest("worker.js"),
                 "example.json": digest("example.json"),
                 "config.json": digest("config.json")})

html = (DEST / "index.html").read_text()
for asset in ("app.js", "style.css", "favicon.svg"):
    html = html.replace(f'./{asset}"', f'./{asset}?v={digest(asset)}"')
(DEST / "index.html").write_text(html)
(DEST / ".nojekyll").touch()
print(f"Built {DEST}")
