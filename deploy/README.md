# Deploy the GUI and live retrieval service

The GUI runs on GitHub Pages. Live trajectories require the included Python service on a host that can run a container and make outbound HTTPS requests. The service has no credentials or database requirement. This repository supplies deployment files; no service URL is provisioned automatically.

## 1. Host the retrieval service

Build the included Dockerfile:

```sh
docker build -t solarconflux .
docker run --rm -p 8080:8080 \
  -e SOLARCONFLUX_ALLOWED_ORIGINS=https://emmavellard.github.io \
  solarconflux
```

The container listens on `PORT` (default 8080). Put it behind the host's HTTPS reverse proxy. Check `GET /api/health`; the GUI uses `POST /api/trajectories`. Allow only the intended site origins, comma-separated, with no URL path or trailing slash. CORS origins identify a website, not an individual repository path.

Run **one service instance** so its query lock serializes JPL calls. Multiple replicas would require a shared queue and cache that are not included. Configure request limits at the host/reverse proxy before offering an unrestricted public endpoint: CORS is a browser restriction, not authentication. The bundled stdlib HTTP server is intended behind that proxy, not as a standalone public TLS server.

The service rejects arbitrary URLs and unsupported bodies, bounds intervals/sample counts/request size, caches responses (24 hours, up to 32 entries/64 MB), returns 429 while busy, and backs off after upstream errors. Service restarts discard only the cache; user history remains in each browser. Ensure the hosting request timeout permits ephemeris retrieval.

## 2. Configure GitHub Pages

1. In repository **Settings → Secrets and variables → Actions → Variables**, create `SOLARCONFLUX_API_URL` with the full HTTPS endpoint, for example `https://YOUR-SERVICE-HOST/api/trajectories`.
2. In **Settings → Pages**, choose **GitHub Actions** as the source.
3. Push the reviewed changes to `main`. The included `pages.yml` runs tests, builds `dist`, and deploys it. Pull requests only test/build.
4. Verify the published page retrieves a short two-body period, saves it in History, and reopens it after reload. Local checks do not substitute for this deployment check.

The build writes the repository variable into `dist/config.json`. Changing the variable requires another build. Without a configured endpoint, the public page can still screen bundled/imported data and explains that live retrieval is unavailable.

For a manual build:

```sh
SOLARCONFLUX_API_URL=https://YOUR-SERVICE-HOST/api/trajectories python scripts/build_web.py
```

Local development defaults to `/api/trajectories` when served at localhost or 127.0.0.1. Use `python -m solarconflux.server --port 8765` after building to serve both GUI and retrieval API.
