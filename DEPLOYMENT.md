# TripPilot deployment

Target: Ubuntu 22.04, Docker Compose, public IP `47.108.74.69`.

The production layout is:

- Repository and Compose project: `/opt/trippilot`
- `frontend`: Nginx serving the built Vue app on public port 80
- `backend`: FastAPI on port 8000 inside the private Compose network only
- Browser API requests: relative URL `/api/v1`
- Container API upstream: `http://backend:8000`

## Configuration

Create the production configuration without committing it:

```bash
cp .env.example .env
chmod 600 .env
```

Set the real LLM, AMap Web Service, AMap Web JS API, and AMap JS security
credentials. The frontend Web JS API key is expected to appear in the built
JavaScript bundle, so protect it with the matching AMap domain whitelist. The
JS security code remains a runtime variable used only by the Nginx proxy.

## Start

The host Nginx service must not occupy port 80:

```bash
systemctl disable --now nginx
docker compose up -d --build
docker compose ps
```

After deployment, verify:

```bash
curl http://127.0.0.1/health
curl http://47.108.74.69/health
```

## Update

```bash
git pull --ff-only
docker compose up -d --build
```

View logs with `docker compose logs -f --tail=100`.
