# TripPilot deployment

Target: Ubuntu 22.04, Nginx, systemd, public IP `47.108.74.69`.

The production layout is:

- Repository and Python environment: `/opt/trippilot`
- Vue static files: `/var/www/trippilot`
- FastAPI: `127.0.0.1:8000` (not exposed publicly)
- Nginx: public ports 80/443
- Backend service user and home: `trippilot`, `/var/lib/trippilot`

Do not commit the real root `.env`, `frontend/.env.production`, or the Nginx
AMap secret snippet. The frontend Web JS API key is expected to appear in the
built JavaScript bundle; protect it with the matching AMap domain whitelist.
