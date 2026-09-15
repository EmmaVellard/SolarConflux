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
html = (DEST / "index.html").read_text()
for asset in ("app.js", "style.css", "favicon.svg"):
    digest = hashlib.sha256((DEST / asset).read_bytes()).hexdigest()[:12]
    html = html.replace(f'./{asset}"', f'./{asset}?v={digest}"')
(DEST / "index.html").write_text(html)
(DEST / ".nojekyll").touch()
print(f"Built {DEST}")
