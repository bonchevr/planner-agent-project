# Planner Agent — Production Deployment Runbook (Fly.io)

> Last updated: June 2025
> Platform: [Fly.io](https://fly.io) — Docker-native PaaS
> Database: Fly Postgres (PostgreSQL 16, self-managed on Fly infrastructure)

---

## 1. Quick Reference

| What | Command |
|------|---------|
| Deploy latest commit | `fly deploy` |
| Tail live logs | `fly logs` |
| SSH into app VM | `fly ssh console` |
| Connect to Postgres | `fly postgres connect -a planner-agent-db` |
| List secrets | `fly secrets list` |
| Scale machines | `fly scale count 2` |
| View releases | `fly releases` |

---

## 2. Prerequisites

### 2.1 Tooling

| Requirement | Notes |
|-------------|-------|
| [flyctl CLI](https://fly.io/docs/hands-on/install-flyctl/) | `curl -L https://fly.io/install.sh \| sh` |
| Docker Engine 24+ | For local dev/testing |
| Python 3.11 | For generating `SECRET_KEY` |

### 2.2 Account Setup

1. Create a free account at <https://fly.io>  
   _(a credit card is required but not charged within the free allowance)_
2. Log in: `fly auth login`
3. Verify: `fly auth whoami`

---

## 3. Environment Variables & Secrets

### 3.1 Non-secret config (stored in `fly.toml` [env])

| Variable | Value | Notes |
|----------|-------|-------|
| `APP_ENV` | `production` | Enables JSON logs, production error pages |
| `PORT` | `8000` | Internal port Uvicorn listens on |
| `WEB_WORKERS` | `2` | Safe for 256 MB VM; increase when upgrading memory |

### 3.2 Secrets (inject with `fly secrets set` — **never** in `fly.toml`)

| Secret | How to set |
|--------|-----------|
| `DATABASE_URL` | Set automatically by `fly postgres attach` |
| `SECRET_KEY` | `fly secrets set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"` |
| `BASE_URL` | `fly secrets set BASE_URL="https://<app-name>.fly.dev"` |

> ⚠️ **Never** commit `SECRET_KEY` or `DATABASE_URL` to source control. Rotate `SECRET_KEY` immediately if exposed — all active sessions will be invalidated.

---

## 4. One-Time Setup (First Deployment)

### Step 1 — Install flyctl

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

### Step 2 — Edit `fly.toml`

Open `fly.toml` at the repo root and change two values:

```toml
app = "your-unique-app-name"   # must be globally unique on Fly
primary_region = "lhr"         # lhr · iad · fra · sea · sin (see §14)
```

### Step 3 — Create the Fly app

```bash
# Registers the app name; uses the existing fly.toml. Does NOT deploy.
fly launch --no-deploy
```

### Step 4 — Create Fly Postgres

```bash
# Provisions a PostgreSQL 16 instance as a separate Fly app.
# shared-cpu-1x + 256 MB + 1 GB disk = within the free allowance.
fly postgres create \
  --name planner-agent-db \
  --region lhr \
  --vm-size shared-cpu-1x \
  --volume-size 1 \
  --initial-cluster-size 1
```

> Use the same region as your app to minimise latency.

### Step 5 — Attach Postgres

```bash
# Automatically sets DATABASE_URL as a Fly secret on the app.
fly postgres attach planner-agent-db --app your-unique-app-name
```

The app normalises the `postgres://` URL to `postgresql://` automatically
(handled in `app/config.py`) so no manual adjustment is needed.

### Step 6 — Set remaining secrets

```bash
fly secrets set \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  BASE_URL="https://your-unique-app-name.fly.dev" \
  --app your-unique-app-name
```

### Step 7 — Deploy

```bash
fly deploy
```

Fly will:
1. Build the Docker image from `Dockerfile`
2. Push it to the Fly container registry
3. Start a new VM in `primary_region`
4. Run `alembic upgrade head` (via `entrypoint.sh`) before accepting traffic
5. Run the `/health` check; the old machine is replaced only if the new one is healthy

---

## 5. Verifying the Deployment

```bash
# Health check — should return {"status": "ok", "version": "0.1.0"}
curl -s https://your-unique-app-name.fly.dev/health | python3 -m json.tool

# Confirm TLS and security headers
curl -sI https://your-unique-app-name.fly.dev/ | grep -Ei "x-content-type|x-frame|referrer|strict-transport"
```

Expected response headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000  ← added by Fly's edge proxy
```

---

## 6. Every-Day Deploy

```bash
git push origin main   # CI runs lint + tests first
fly deploy             # deploy after CI passes (or use auto-deploy — see §10)
```

---

## 7. Logs & Monitoring

```bash
# Tail live logs (JSON format in production)
fly logs --app your-unique-app-name

# Prometheus metrics (requires auth — not public)
curl https://your-unique-app-name.fly.dev/metrics
```

Metrics exposed: `http_requests_total` (counter) and `http_request_duration_seconds` (histogram).

---

## 8. Managing Secrets

```bash
# List current secrets (names only — values are never shown)
fly secrets list --app your-unique-app-name

# Rotate the secret key (invalidates all existing sessions)
fly secrets set \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  --app your-unique-app-name

# Remove a secret
fly secrets unset SOME_SECRET --app your-unique-app-name
```

---

## 9. Database Management

```bash
# Open an interactive psql session
fly postgres connect -a planner-agent-db

# View Postgres logs
fly logs --app planner-agent-db

# Run a one-off Alembic migration manually (normally automatic on deploy)
fly ssh console --app your-unique-app-name -C "alembic upgrade head"
```

### 9.1 Backups

Fly Postgres does **not** provide automated backups by default. Recommended approach:

```bash
# Dump to a local SQL file via fly proxy
fly proxy 5432:5432 -a planner-agent-db &
pg_dump "postgresql://postgres:<password>@localhost:5432/planner_agent" \
  -f backup-$(date +%Y%m%d-%H%M).sql
kill %1  # stop the proxy
```

The Postgres password is in the `DATABASE_URL` secret — extract it with:

```bash
fly ssh console --app your-unique-app-name -C "printenv DATABASE_URL"
```

For automated backups, consider adding a cron job that runs `pg_dump` and uploads to S3/R2.

---

## 10. GitHub Actions Auto-Deploy

Add a `deploy` job to `.github/workflows/ci.yml` after the `lint-and-test` job:

```yaml
  deploy:
    name: Deploy to Fly.io
    needs: [lint-and-test]   # only deploy if tests + lint pass
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: fly deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

**Setup:**
1. Generate a deploy token: `fly tokens create deploy -x 999999h`
2. Add it as a repository secret named `FLY_API_TOKEN` in  
   GitHub **Settings → Secrets and variables → Actions → New repository secret**

---

## 11. Scaling

```bash
# Scale to 2 app machines (zero-downtime rolling deploy)
fly scale count 2 --app your-unique-app-name

# Upgrade VM memory (e.g., to 512 MB for WEB_WORKERS=4)
fly scale vm shared-cpu-1x --memory 512 --app your-unique-app-name

# Check current machine status
fly status --app your-unique-app-name
```

> The free allowance covers **3 shared-cpu-1x 256 MB machines per organisation**.
> This app uses 2 (1 app VM + 1 Postgres VM), so you can scale the app to 2 replicas at no extra cost.

---

## 12. Rollback

```bash
# List releases with image tags
fly releases --app your-unique-app-name

# Roll back to a specific image (e.g., v5)
fly deploy --image registry.fly.io/your-unique-app-name:deployment-v5
```

For a code-level rollback:

```bash
git revert HEAD         # revert the bad commit
git push origin main    # triggers CI + auto-deploy (if §10 is configured)
```

---

## 13. OWASP Security Checklist (v0.4+)

| # | Control | Status | Notes |
|---|---------|--------|-------|
| A01 | Broken Access Control | ✅ | Per-user ownership on all routes; CSRF tokens on every state-changing form; public share links are read-only |
| A02 | Cryptographic Failures | ✅ | Passwords hashed with bcrypt (cost 12); sessions signed with itsdangerous `TimestampSigner`; HTTPS enforced by Fly edge proxy |
| A03 | Injection — SQL | ✅ | SQLModel/SQLAlchemy parameterised queries throughout; no raw SQL |
| A03 | Injection — XSS | ✅ | Markdown rendered via `mistune` + `bleach` allowlist; Jinja2 auto-escapes all other output |
| A03 | Injection — Command | ✅ | No shell execution in the application |
| A04 | Insecure Design | ✅ | Review `agents/code-review.agent.md` before each release |
| A05 | Security Misconfiguration | ✅ | Security headers middleware (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`); non-root container user (`appuser`); no debug mode in production |
| A06 | Vulnerable Components | ⚠️ | Run `pip-audit -r requirements.txt` before each release; all dependencies are pinned |
| A07 | Auth Failures | ✅ | bcrypt password hashing; session expiry via `TimestampSigner`; CSRF protection on all mutations; secure password-reset tokens |
| A08 | Software Integrity | ✅ | Dependencies pinned; Docker image built from source; GitHub Actions CI validates every commit |
| A09 | Logging & Monitoring | ✅ | loguru JSON logs in production; Prometheus metrics at `/metrics`; Fly health checks every 30 s |
| A10 | SSRF | ✅ | App makes no outbound HTTP requests |

**Recommended before first public announcement:**
- [ ] Run `pip-audit -r requirements.txt` and remediate any high/critical CVEs
- [ ] Enable Fly.io health-check alerts / on-call notifications
- [ ] Configure `pg_dump` backup schedule (see §9.1)

---

## 14. Regions

| Code | Location | Good for |
|------|----------|---------|
| `lhr` | London, UK | Europe / UK users |
| `iad` | Ashburn, VA | East Coast USA |
| `sea` | Seattle, WA | West Coast USA |
| `fra` | Frankfurt, DE | EU-GDPR-sensitive workloads |
| `sin` | Singapore | Asia-Pacific |

Change `primary_region` in `fly.toml` and run `fly deploy` to migrate.

---

## 15. Cost Breakdown (Fly.io Free Tier)

| Resource | Free Allowance | This App Uses | Monthly Cost |
|----------|--------------|---------------|-------------|
| shared-cpu-1x 256 MB VMs | 3 machines | 1 app VM | $0 |
| Fly Postgres (shared-cpu-1x 256 MB) | 3 machines | 1 Postgres VM | $0 |
| Outbound transfer | 100 GB | < 1 GB (estimated) | $0 |
| **Total** | | | **$0 / month** |

> Pricing correct as of mid-2025. Free allowance is per Fly organisation.
> See <https://fly.io/docs/about/pricing/> for current rates.

---

## 16. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `fly deploy` fails health check | App crashed on start (missing secret, migration error) | Run `fly logs` immediately after to catch the error |
| `DATABASE_URL` scheme error | `postgres://` not normalised | Handled in `app/config.py`; check `fly logs` if it persists |
| 500 errors | Unhandled exception | `fly logs --app your-unique-app-name` for the stack trace |
| Sessions not persisting | `SECRET_KEY` rotated; old cookies invalid | Expected after rotation; users must re-login |
| `alembic upgrade head` fails | DB not ready or migration conflict | `fly postgres connect` and inspect Alembic version table |
| Share links return 404 | `BASE_URL` secret wrong | `fly secrets set BASE_URL=https://<app>.fly.dev` |
| Forgot-password link broken | `BASE_URL` secret missing | Same as above |

---

## 17. Performance Baseline

Measured on a shared-cpu-1x 256 MB Fly machine (2 Uvicorn workers):

| Endpoint | p50 | p99 |
|----------|-----|-----|
| `GET /` | < 10 ms | < 30 ms |
| `POST /generate` | < 30 ms | < 80 ms |
| `GET /gameplan/{id}` | < 15 ms | < 40 ms |

Gameplan render target: ≤ 200 ms ✅ (validated by `TestPerformance::test_generate_and_render_under_200ms`).
