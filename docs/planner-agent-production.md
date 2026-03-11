# Planner Agent — Production Deployment Runbook (Fly.io)

> Last updated: March 2026
> Platform: [Fly.io](https://fly.io) — Docker-native PaaS
> Database: [Neon](https://neon.tech) — managed serverless PostgreSQL 16 (external, never auto-stops)

---

## 1. Quick Reference

| What | Command |
|------|---------|
| Deploy latest commit | `flyctl deploy` |
| Tail live logs | `flyctl logs` |
| SSH into app VM | `flyctl ssh console` |
| Connect to Neon (psql) | Connect via your Neon dashboard or `psql "$DATABASE_URL"` |
| List secrets | `flyctl secrets list` |
| Scale machines | `flyctl scale count 2` |
| View releases | `flyctl releases` |

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
| `WEB_WORKERS` | `2` | Suitable for 1 GB VM; increase if upgrading and load-testing |

### 3.2 Secrets (inject with `flyctl secrets set` — **never** in `fly.toml`)

| Secret | How to set |
|--------|----------|
| `DATABASE_URL` | `flyctl secrets set DATABASE_URL="<your-neon-connection-string>"` |
| `SECRET_KEY` | `flyctl secrets set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"` |
| `BASE_URL` | `flyctl secrets set BASE_URL="https://planner-agent.fly.dev"` |
| `SMTP_HOST` | `flyctl secrets set SMTP_HOST="smtp.resend.com"` |
| `SMTP_PORT` | `flyctl secrets set SMTP_PORT="465"` |
| `SMTP_USER` | `flyctl secrets set SMTP_USER="resend"` |
| `SMTP_PASSWORD` | `flyctl secrets set SMTP_PASSWORD="<your-resend-api-key>"` |
| `SMTP_FROM` | `flyctl secrets set SMTP_FROM="Planner Agent <onboarding@resend.dev>"` |

> ⚠️ **Never** commit `SECRET_KEY`, `DATABASE_URL`, or `SMTP_PASSWORD` to source control. Rotate `SECRET_KEY` immediately if exposed — all active sessions will be invalidated.

> 📧 **Email notes:** The free Resend account uses `onboarding@resend.dev` as sender, which can only deliver to the account owner’s verified email. To send to any address, verify a custom domain at [resend.com/domains](https://resend.com/domains) and update `SMTP_FROM` accordingly.

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
app = "planner-agent"   # must be globally unique on Fly
primary_region = "lhr"         # lhr · iad · fra · sea · sin (see §14)
```

### Step 3 — Create the Fly app

```bash
# Registers the app name; uses the existing fly.toml. Does NOT deploy.
fly launch --no-deploy
```

### Step 4 — Create a Neon database

1. Sign up at <https://neon.tech> (free tier, no credit card required)
2. Create a new project and a database (e.g., `planner_agent`)
3. Copy the **connection string** from the Neon dashboard — it looks like:  
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/planner_agent?sslmode=require`

> Neon is serverless and never auto-stops, making it ideal for low-traffic production workloads.

### Step 5 — Set secrets

```bash
flyctl secrets set \
  DATABASE_URL="<your-neon-connection-string>" \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  BASE_URL="https://planner-agent.fly.dev" \
  SMTP_HOST="smtp.resend.com" \
  SMTP_PORT="465" \
  SMTP_USER="resend" \
  SMTP_PASSWORD="<your-resend-api-key>" \
  SMTP_FROM="Planner Agent <onboarding@resend.dev>"
```

The app normalises `postgres://` to `postgresql://` automatically (handled in `app/config.py`) so either URL format works.

### Step 6 — Deploy

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
curl -s https://planner-agent.fly.dev/health | python3 -m json.tool

# Confirm TLS and security headers
curl -sI https://planner-agent.fly.dev/ | grep -Ei "x-content-type|x-frame|referrer|strict-transport"
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
fly logs --app planner-agent

# Prometheus metrics (requires auth — not public)
curl https://planner-agent.fly.dev/metrics
```

Metrics exposed: `http_requests_total` (counter) and `http_request_duration_seconds` (histogram).

---

## 8. Managing Secrets

```bash
# List current secrets (names only — values are never shown)
fly secrets list --app planner-agent

# Rotate the secret key (invalidates all existing sessions)
fly secrets set \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  --app planner-agent

# Remove a secret
fly secrets unset SOME_SECRET --app planner-agent
```

---

## 9. Database Management

```bash
# Connect to the Neon database via psql (requires DATABASE_URL)
psql "$DATABASE_URL"

# Or extract the URL from Fly secrets and use it locally
fly ssh console --app planner-agent -C "printenv DATABASE_URL"

# Run a one-off Alembic migration manually (normally automatic on deploy)
fly ssh console --app planner-agent -C "alembic upgrade head"
```

### 9.1 Backups

Neon provides **automated daily backups** and **point-in-time restore** (PITR) on the free tier. No manual backup setup is required. You can also trigger a manual snapshot from the Neon dashboard.

For an on-demand local dump:

```bash
# Export DATABASE_URL first (from fly ssh console or your local .env)
pg_dump "$DATABASE_URL" -f backup-$(date +%Y%m%d-%H%M).sql
```

---

## 10. GitHub Actions CI/CD Pipeline

The repository uses a single workflow file:

| File | Trigger | Jobs |
|------|---------|------|
| `fly-deploy.yml` | Push → `main` | 1. Lint & Test → 2. Push image to Docker Hub (parallel) + 3. Deploy to Fly.io (parallel) |

### Required GitHub Actions secrets

| Secret | Purpose | How to obtain |
|--------|---------|---------------|
| `FLY_API_TOKEN` | Fly.io deploy | `flyctl tokens create deploy -x 999999h` |
| `DOCKERHUB_TOKEN` | Push image to Docker Hub | Docker Hub → Account Settings → Personal access tokens |

Add both under **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**.

The Docker Hub image is published as `bonchevr/planner-agent:latest` and `bonchevr/planner-agent:sha-<commit>` on every successful push to `main`.

---

## 11. Scaling

```bash
# Scale to 2 app machines (zero-downtime rolling deploy)
fly scale count 2 --app planner-agent

# Upgrade VM memory (e.g., to 2 GB for WEB_WORKERS=4)
fly scale vm shared-cpu-1x --memory 2048 --app planner-agent

# Check current machine status
fly status --app planner-agent
```

> The free allowance covers **3 shared-cpu-1x machines per organisation**.
> This app uses 1 (app VM only — database is on Neon), so you can scale to 3 replicas at no extra cost.

---

## 12. Rollback

```bash
# List releases with image tags
fly releases --app planner-agent

# Roll back to a specific image (e.g., sha-abc1234 from Docker Hub)
fly deploy --image bonchevr/planner-agent:sha-abc1234
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

## 15. Cost Breakdown

| Resource | Free Allowance | This App Uses | Monthly Cost |
|----------|--------------|---------------|--------------|
| shared-cpu-1x 1 GB VM | 3 machines | 1 app VM | $0 |
| Neon PostgreSQL | Free tier (0.5 GB storage, unlimited connections) | 1 project | $0 |
| Outbound transfer | 100 GB | < 1 GB (estimated) | $0 |
| **Total** | | | **$0 / month** |

> Fly.io pricing correct as of mid-2025. The 1 GB VM is within the free allowance (3 shared-cpu-1x machines per org).
> Neon free tier: <https://neon.tech/pricing>. Fly.io pricing: <https://fly.io/docs/about/pricing/>.

---

## 16. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `fly deploy` fails health check | App crashed on start (missing secret, migration error) | Run `fly logs` immediately after to catch the error |
| `DATABASE_URL` scheme error | `postgres://` not normalised | Handled in `app/config.py`; check `fly logs` if it persists |
| 500 errors | Unhandled exception | `fly logs --app planner-agent` for the stack trace |
| Sessions not persisting | `SECRET_KEY` rotated; old cookies invalid | Expected after rotation; users must re-login |
| `alembic upgrade head` fails | DB not ready or migration conflict | `fly postgres connect` and inspect Alembic version table |
| Share links return 404 | `BASE_URL` secret wrong | `flyctl secrets set BASE_URL=https://planner-agent.fly.dev` |
| Forgot-password link broken | `BASE_URL` secret missing / wrong | `flyctl secrets set BASE_URL=https://planner-agent.fly.dev` |

---

## 17. Performance Baseline

Measured on a shared-cpu-1x 1 GB Fly machine (2 Uvicorn workers):

| Endpoint | p50 | p99 |
|----------|-----|-----|
| `GET /` | < 10 ms | < 30 ms |
| `POST /generate` | < 30 ms | < 80 ms |
| `GET /gameplan/{id}` | < 15 ms | < 40 ms |

Gameplan render target: ≤ 200 ms ✅ (validated by `TestPerformance::test_generate_and_render_under_200ms`).
