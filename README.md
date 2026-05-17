# Leads Management Portal

A Django 5 portal that ingests leads from WordPress sites, distributes them to
clients via subscriptions or one-off orders, and gives super admins, admins,
agents, and clients dedicated UIs for the parts of the system they own.

Stack: Django 5, DRF, HTMX + Bootstrap 5, PostgreSQL, Redis + Celery, Stripe,
SendGrid, AWS S3 (media), Railway (hosting). WhiteNoise serves static files
out of the web process.

---

## Apps

| App | Purpose |
|-----|---------|
| `apps.core` | Shared utilities, `TimeStampedModel`, `SystemSetting`, template tags, middleware, healthz |
| `apps.accounts` | Custom email-based User + 4 roles (SUPER_ADMIN / ADMIN / AGENT / CLIENT), auth flows |
| `apps.leads` | Lead model, ingest API, distribution, quality scoring, replacements, CSV export |
| `apps.clients` | Client profile, Wallet + WalletTransaction, Subscription |
| `apps.billing` | Order, Invoice, Stripe webhook + idempotency, wallet/order services |
| `apps.agents` | Agent profile, LeadAssignment, CallLog |
| `apps.sweepstakes` | Sweepstakes campaigns + winner draw |
| `apps.notifications` | Notification + ActivityLog, email service, unread-count endpoint |
| `apps.portals.{super_admin,admin_portal,agent,client}` | Per-role portal views, urls, templates |

---

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in at least SECRET_KEY. SQLite is the default if DATABASE_URL is empty.
python manage.py migrate
python manage.py seed              # creates super admin + SystemSettings (incl. lead_ingest_api_key)
python manage.py runserver
```

Dev settings (`config.settings.dev`) ship with:
- SQLite at `db.sqlite3`
- Console email backend (welcome / reset / order emails print to the server log)
- `CELERY_TASK_ALWAYS_EAGER=True` so tasks run inline — no Redis needed

To run with a real Celery worker locally, set `CELERY_TASK_ALWAYS_EAGER=false`
in `.env`, start Redis (e.g. `docker run -p 6379:6379 redis`), then:

```bash
celery -A config worker -l info
```

---

## Production deployment — Railway

1. **Push to GitHub**
   ```bash
   git init && git add . && git commit -m 'initial'
   git remote add origin <repo-url> && git push -u origin main
   ```

2. **Railway → New Project → Deploy from GitHub**, select this repo.

3. **Add services**: PostgreSQL (provisions `DATABASE_URL`) and Redis
   (provisions `REDIS_URL`). Railway injects these into the Django service.

4. **Set env vars on the Django service** (see reference below). Minimum:
   `SECRET_KEY`, `DJANGO_SETTINGS_MODULE=config.settings.prod`,
   `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `STRIPE_*`, `SENDGRID_API_KEY`.

5. **Deploy.** The `release` process runs `python manage.py migrate --noinput`
   automatically. Watch logs for the migration output.

6. **Seed once** (Railway service shell):
   ```bash
   python manage.py seed
   ```

7. **Custom domain**: Settings → Domains → Add `portal.yourdomain.com`. Set the
   CNAME record at your DNS provider per Railway's instructions. Add the same
   domain to `ALLOWED_HOSTS` and a full `https://...` entry to
   `CSRF_TRUSTED_ORIGINS`. Redeploy.

8. **Stripe**: Dashboard → Developers → Webhooks → Add endpoint
   `https://<your-domain>/webhooks/stripe/`. Select events:
   `payment_intent.succeeded`, `customer.subscription.created`,
   `customer.subscription.updated`, `customer.subscription.deleted`,
   `invoice.paid`. Copy the signing secret to `STRIPE_WEBHOOK_SECRET`.

9. **SendGrid**: verify the *sender domain* (not just a single email).
   Add the SPF / DKIM / DMARC records SendGrid generates to your DNS so
   transactional emails don't land in spam.

10. **WordPress plugin**: install `wordpress-plugin/portal-lead-sync.php`,
    fill in the prod API URL + the `lead_ingest_api_key` value, point at the
    form ID, save, click **Send test lead**.

Railway uses `Procfile` for process types and `railway.json` for the build /
healthcheck. The web service hits `/healthz/` on each redeploy.

### Per-service start commands (set on Railway, or scale via Procfile types)

| Process | Command |
|---------|---------|
| web | `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3 --access-logfile - --error-logfile -` |
| worker | `celery -A config worker -l info` |
| beat | `celery -A config beat -l info` |
| release | `python manage.py migrate --noinput` |

---

## Environment variable reference

| Var | When | Purpose |
|-----|------|---------|
| `SECRET_KEY` | always | Django signing key |
| `DJANGO_SETTINGS_MODULE` | always | `config.settings.dev` or `config.settings.prod` |
| `DEBUG` | optional | Force-disable debug in dev |
| `DATABASE_URL` | always (prod) | Postgres URL; SQLite fallback in dev |
| `ALLOWED_HOSTS` | prod | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | prod | Comma-separated full origins (`https://…`) |
| `REDIS_URL` | prod | Redis URL — used for cache + Celery broker |
| `CELERY_BROKER_URL` | optional | Override the Celery broker (defaults to `REDIS_URL`) |
| `CELERY_RESULT_BACKEND` | optional | Where to store task results |
| `CELERY_TASK_ALWAYS_EAGER` | dev | `true` runs tasks inline, no worker needed |
| `SENDGRID_API_KEY` | prod | SMTP auth password for `apikey` user |
| `DEFAULT_FROM_EMAIL` | prod | `noreply@<verified-domain>` |
| `STRIPE_PUBLIC_KEY` | prod | Publishable key (mounts Stripe Elements) |
| `STRIPE_SECRET_KEY` | prod | Server-side Stripe key |
| `STRIPE_WEBHOOK_SECRET` | prod | Webhook signing secret (`whsec_…`) |
| `USE_S3` | optional | `true` to put media on S3 |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | `USE_S3=true` | IAM credentials |
| `AWS_STORAGE_BUCKET_NAME` | `USE_S3=true` | Bucket name |
| `AWS_S3_REGION_NAME` | `USE_S3=true` | e.g. `us-east-1` |
| `PORTAL_BASE_URL` | prod | Full URL used in outbound emails |
| `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` | first seed | Used by `python manage.py seed` |

---

## WordPress plugin installation

The portal ships with `wordpress-plugin/portal-lead-sync.php`. To install:

1. Copy the file into `wp-content/plugins/portal-lead-sync/` on the WP host.
2. **Plugins → Activate** *Portal Lead Sync*.
3. **Settings → Portal Lead Sync** and fill in:
   - **Portal API URL** — `https://<your-domain>/api/v1/leads/ingest`
   - **API Key** — value of `lead_ingest_api_key` from Super Admin → Settings
   - **Default Niche** — e.g. `solar-usa`
   - **Source Type** — `SOLAR` or `SWEEPSTAKES`
   - **Form plugin** — WPForms / Contact Form 7 / Elementor Pro / Generic
   - **Form ID** — leave blank for "all forms of this plugin"
   - **Field mapping** — one `portalField=sourceField` per line, e.g.
     ```
     firstName=name
     lastName=last_name
     email=email
     phone=phone
     state=state
     monthlyBill=monthly_bill
     isHomeowner=homeowner
     ```
4. Click **Send test lead** — you should see a success notice and a lead appear
   in Super Admin → Leads on the portal.

If you regenerate the ingest API key on the portal (Super Admin → Settings →
API Keys → Regenerate), update the WordPress plugin's *API Key* immediately;
old keys are rejected with HTTP 401.

---

## First-time setup checklist

1. `python manage.py seed` — creates the super admin and `SystemSetting`
   defaults (incl. `lead_ingest_api_key`, niche pricing, replacement windows).
2. Log in at `/login/` with the seeded super admin and change the password.
3. **Super Admin → Settings → Pricing** — adjust the default per-niche shared
   and exclusive prices.
4. **Super Admin → Clients → New** — create your first client (a User + Client
   + Wallet row are created atomically and a welcome email is dispatched).
5. **Super Admin → Settings → API Keys** — copy `lead_ingest_api_key`.
6. **Install the WP plugin** with that key + the portal API URL.
7. **Stripe**: set test keys locally, then production keys in Railway. Add the
   `/webhooks/stripe/` endpoint in the Stripe dashboard and copy the signing
   secret.
8. **Send a test lead** from the WP plugin and confirm it appears in
   `/super/leads/`.

---

## Health check

`GET /healthz/` returns `200 {"status": "ok"}` after a `SELECT 1` against the
database. Wired into `railway.json` as `healthcheckPath`; use the same URL for
external uptime monitors.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| 401 from `/api/v1/leads/ingest` | API key missing or rotated — copy from Settings → API Keys |
| 400 with `phone must contain 10 digits` | WP field mapping points at the wrong source key |
| Sweeps lead not bound to a campaign | The lead's `niche` doesn't match any **ACTIVE** sweepstakes whose `[start_date, end_date]` covers today — check the campaign window (the portal uses Django's TZ-aware `localdate()`) |
| Stripe webhook 400 "Bad signature" | `STRIPE_WEBHOOK_SECRET` in env doesn't match the value shown in Stripe's webhook detail page |
| Welcome / reset emails not received | In prod, SendGrid sender domain isn't verified; in dev they print to the console |
| Tasks never fire in prod | Celery worker process not running — start the `worker` process type or scale it to ≥1 in Railway |
| `DisallowedHost` after adding a custom domain | Add the new host to `ALLOWED_HOSTS` *and* `CSRF_TRUSTED_ORIGINS` and redeploy |
| Static files 404 in prod | `collectstatic` skipped — Railway should run it via the build command; verify in deploy logs |
| `/healthz/` returns 503 | DB unreachable; check `DATABASE_URL` and the Postgres service status |

---

## Useful management commands

```bash
python manage.py seed                  # idempotent: super admin + SystemSettings
python manage.py check --deploy        # production-readiness checks
python manage.py collectstatic --noinput
python manage.py migrate --noinput
celery -A config worker -l info
celery -A config beat -l info
```


 ┌──────────────────┬──────────────────────┬──────────────────┐
  │       Role       │        Email         │     Password     │
  ├──────────────────┼──────────────────────┼──────────────────┤
  │ Super admin      │ admin@test.local     │ NewPassw0rd!9876 │                                                                                    
  ├──────────────────┼──────────────────────┼──────────────────┤
  │ Client           │ client@test.local    │ ClientPass!9876  │
  │ Client (NewCorp) │ newclient@test.local │ mfKpTQq5CVuCY8Xp │
  ├──────────────────┼──────────────────────┼──────────────────┤
  │ Agent            │ agent1@test.local    │ AgentPass!1234   │
  └──────────────────┴──────────────────────┴──────────────────┘