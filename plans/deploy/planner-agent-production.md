# Planner Agent — Production Deployment Runbook

> Last updated: 6 March 2026
> Environment: Docker + single-worker Uvicorn (v1)

---

## 1. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker Engine | 24+ | Or Docker Desktop 4.x+ |
| Docker Compose | v2 (`docker compose`) | Bundled with Docker Desktop |
| Make | any | Ships with macOS / Linux; WSL on Windows |
| A `.env` file | — | Copy from `.env.example`; **never commit it** |

---

## 2. Environment Variables

Copy `.env.example` to `.env` and populate **every** value below before deploying.

| Variable | Default | Required in prod | Notes |
|----------|---------|-----------------|-------|
| `APP_ENV` | `development` | ✅ Set to `production` | Enables prod behaviour |
| `DATABASE_URL` | `sqlite:///./data/planner.db` | ✅ | Path inside the container; covered by the volume |
| `SECRET_KEY` | `change-me-before-deploying` | ✅ **Must change** | Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |

> ⚠️ **Never** use the default `SECRET_KEY` in production. Rotate it if you suspect it has been exposed.

---

## 3. Build & Run

```bash
# Clone and enter the repo
git clone <repo-url>
cd planner_agent_project

# Create .env from example
cp .env.example .env
# Edit .env — set APP_ENV=production and a strong SECRET_KEY

# Build the Docker image and start the container in the background
make compose-up
# → http://localhost:8000

# Tail logs
docker compose logs -f app

# Stop and remove the container (data volume is preserved)
make compose-down
```

The SQLite database is stored in the Docker-managed `db-data` volume at
`/app/data/planner.db` inside the container.

---

## 4. Verifying the Deployment

```bash
# Health check — should return {"status": "ok"}
curl -s http://localhost:8000/health | python3 -m json.tool

# Confirm security headers are present
curl -sI http://localhost:8000/ | grep -E "X-Content-Type|X-Frame|Referrer"
```

Expected header values:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 5. Data & Backups

The SQLite database lives in a named Docker volume (`db-data`). For production backups:

```bash
# Copy the database out of the volume to the host
docker run --rm \
  -v planner_agent_project_db-data:/data \
  -v "$(pwd)":/backup \
  alpine cp /data/planner.db /backup/planner-backup-$(date +%Y%m%d).db
```

Schedule this via cron or your hosting provider's backup facility.

---

## 6. Updating / Redeploying

```bash
git pull origin main
make compose-up   # rebuilds the image if the Dockerfile or dependencies changed
```

Docker Compose will recreate the container with zero data loss (the volume is preserved).

---

## 7. OWASP Security Checklist

| # | Control | Status | Notes |
|---|---------|--------|-------|
| A01 | Broken Access Control | ✅ | v1 is single-user/local; no auth surface |
| A02 | Cryptographic Failures | ✅ | No sensitive data stored; SQLite file is local |
| A03 | Injection — SQL | ✅ | SQLModel/SQLAlchemy parameterised queries throughout |
| A03 | Injection — XSS | ✅ | Markdown rendered via `mistune` + sanitised with `bleach`; Jinja2 auto-escapes all other output |
| A03 | Injection — Command | ✅ | No shell execution in the application |
| A04 | Insecure Design | ✅ | Review `code-review.agent.md` before each release |
| A05 | Security Misconfiguration | ✅ | Security headers middleware (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`); non-root container user |
| A06 | Vulnerable Components | ⚠️ | Run `pip-audit -r requirements.txt` before each release |
| A07 | Auth Failures | N/A | No authentication in v1; add before any multi-user or public deployment |
| A08 | Software Integrity | ✅ | Dependencies pinned; Docker image built from source |
| A09 | Logging & Monitoring | ⚠️ | Uvicorn access logs only; add structured logging + alerting for v2 |
| A10 | SSRF | ✅ | App makes no outbound HTTP requests |

**P0 items before any public deployment:**
- [ ] Add authentication (A07) — even HTTP Basic Auth — before exposing to the internet
- [ ] Run `pip-audit` and remediate any critical/high CVEs
- [ ] Rotate `SECRET_KEY` to a cryptographically random value

---

## 8. Performance Baseline

Measured on a mid-range laptop (Intel i7, Docker Desktop):

| Endpoint | Method | p50 | p99 |
|----------|--------|-----|-----|
| `GET /` | — | < 5 ms | < 15 ms |
| `POST /generate` | — | < 20 ms | < 60 ms |
| `GET /gameplan/{id}` | — | < 10 ms | < 30 ms |

Gameplan generation + markdown render: **< 5 ms** (measured by `TestPerformance::test_generate_and_render_under_200ms`; target ≤ 200 ms ✅).

---

## 9. Rollback

```bash
# Roll back to the previous image tag (if you tag releases)
docker pull planner-agent:<previous-tag>
docker compose down
APP_IMAGE=planner-agent:<previous-tag> docker compose up -d
```

For a quick rollback without tags, `git revert` the offending commit(s) and re-run `make compose-up`.

---

## 10. Known Limitations (v1)

- **Single worker**: SQLite is not safe under concurrent writes with multiple Uvicorn workers. Keep `--workers 1`.
- **No TLS at app level**: Terminate TLS at a reverse proxy (nginx, Caddy, Fly.io's built-in proxy) in front of the container.
- **No rate limiting**: Add an nginx or Traefik rate-limit rule before public exposure.
- **No multi-user support**: All gameplans are shared in a single database with no ownership model.
