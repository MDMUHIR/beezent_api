# Deploying the Beezents backend on AWS EC2

This guide walks through deploying the Beezents FastAPI backend on a single
AWS EC2 instance with HTTPS, an external/managed PostgreSQL, and persistent
media storage.

## Architecture

```
                        ┌───────────────────────────── EC2 instance ─────────────────────────────┐
  Browser ──HTTPS──▶ nginx ──▶ api (FastAPI, port 8000)                                          │
                      ▲         │  ▲                                                            │
                      │         │  └── media-data volume (EBS-backed local storage)              │
                      └── certbot renews the TLS certificate every 12h; nginx reloads every 6h   │
   (80/443 open in the security group)                                                           │
                        ▲                                                                        │
                        └── Amazon RDS PostgreSQL (external, managed) ───────────────────────────┘
```

- **nginx** terminates TLS (Let's Encrypt), proxies `/` to the API, and
  redirects HTTP → HTTPS.
- **api** is the containerized FastAPI app. Its entrypoint runs
  `alembic upgrade head` before starting Uvicorn.
- **certbot** keeps the Let's Encrypt certificate renewed (12h loop); nginx
  reloads every 6h so renewed certificates are picked up.
- **PostgreSQL** is external (Amazon RDS recommended). The API connects with
  the async `asyncpg` driver.
- **Media** is stored on the instance's EBS volume through the `media-data`
  named volume. For multi-instance/autoscaling use S3 or Cloudflare R2 instead.

## Prerequisites

1. **AWS account** and an **EC2 instance**:
   - AMI: Ubuntu 24.04 LTS (or 22.04), any size (t3.micro is enough to start).
   - Storage: at least 20 GB EBS (media is stored here).
   - **Security group** must allow:
     - `22` (SSH) from your IP only,
     - `80` and `443` from anywhere (`0.0.0.0/0`),
     - no other inbound ports (the API is not exposed directly).
2. **A domain** (or subdomain) pointing to the instance's **Elastic IP**,
   e.g. `api.beezents.com` → `A` record → instance public IP.
3. **Amazon RDS PostgreSQL** (recommended) or any reachable PostgreSQL:
   - Create a PostgreSQL instance (e.g. `db.t3.micro`, 20 GB gp3).
   - Note the **endpoint**, **port** (5432), **master username/password**, and
     **database name** (`beezents`).
   - Allow the EC2 instance's security group to reach the RDS security group.
4. **Docker + docker compose** on the instance (see below).

## Step 1 — Launch an EC2 instance and install Docker

```sh
# SSH into the instance
ssh ubuntu@<INSTANCE_IP>

# Install Docker and the compose plugin
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu   # re-login afterwards
```

## Step 2 — Get the code and configure environment

```sh
git clone https://github.com/MDMUHIR/beezent_api.git
cd beezent_api/backend

cp .env.production.example .env.production
nano .env.production
```

Edit `.env.production`:

- `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` — the RDS (or
  other PostgreSQL) connection details, e.g.:
  ```
  DB_HOST=beezents-db.CLUSTER.ap-southeast-1.rds.amazonaws.com
  DB_PORT=5432
  DB_USER=beezents
  DB_PASSWORD=<your-password>
  DB_NAME=beezents
  ```
  The async DSN (`postgresql+asyncpg://…`) is assembled automatically from
  these components, and special characters in the password are URL-encoded.
  Alternatively, set `DATABASE_URL` to a full DSN — it takes precedence.
  (The database itself must already exist; RDS creates the DB you name at
  creation time. The entrypoint only applies migrations.)
- `CORS_ALLOWED_ORIGINS` — the origins of your Next.js frontend, e.g.
  `https://www.beezents.com,https://beezents.com`.
- `TRUSTED_HOSTS` — the domain of **this** API, e.g. `api.beezents.com`.
- `COOKIE_SECURE=true` is already set — do not change it.
- `SEED_DEV_ADMIN=false` is already set — keep it that way in production.
- `UVICORN_WORKERS` — start with `2`.

> `.env.production` is git-ignored and never baked into the image. Keep it
> only on the instance.

## Step 3 — Obtain a TLS certificate (first time only)

```sh
DOMAIN=api.beezents.com EMAIL=admin@beezents.com ./deploy/init-letsencrypt.sh
```

The script generates `deploy/nginx.conf` from the template, creates a dummy
certificate so nginx can boot, requests a real Let's Encrypt certificate via
the HTTP-01 challenge, and reloads nginx.

> Testing? Use `STAGING=1 DOMAIN=... ./deploy/init-letsencrypt.sh` first to
> avoid Let's Encrypt rate limits, then re-run without `STAGING=1`.

## Step 4 — Start the stack

```sh
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

## Step 5 — Verify

```sh
# From the instance:
curl https://api.beezents.com/health
curl https://api.beezents.com/api/v1/health/db

# From anywhere:
curl https://api.beezents.com/docs   # interactive Swagger UI
```

Expected: `{"status":"healthy"}` and `{"status":"healthy"}` for the DB check.

## Day-to-day operations

### Deploying an update

```sh
cd beezent_api/backend
./deploy/deploy.sh
```

`deploy.sh` pulls the latest code (`git pull --ff-only`), rebuilds and
restarts the stack. Migrations run automatically in the container entrypoint.

### Viewing logs

```sh
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f nginx
```

Logs go to stdout/stderr, so you can also stream them to **CloudWatch Logs**
with the CloudWatch agent if desired.

### Backups

- **Database**: RDS automated backups / snapshots (recommended), or
  `pg_dump` scheduled with cron.
- **Media**: snapshot the EBS volume or back up `/app/media`. Because media
  lives in the `media-data` named volume (stored under
  `/var/lib/docker/volumes/beezents_backend_media-data/_data`), back up that
  path or use an EBS snapshot.

## Optional improvements

### Managed TLS with an Application Load Balancer (ALB)

Instead of nginx + certbot, put the API behind an **ALB with an ACM
certificate** (free, auto-renewed by AWS):

1. Keep `docker-compose.prod.yml` but only run the `api` service, or run
   nginx and let the ALB talk to it.
2. Point the ALB's target group at the instance port `80`/`443` and configure
   an HTTP health check on `/health`.
3. Configure `COOKIE_SECURE=true`, `TRUSTED_HOSTS` and `CORS_ALLOWED_ORIGINS`
   with the real domain as before.

### Object storage for media (multi-instance / autoscaling)

The `local` backend writes to the instance disk. For a multi-instance or
autoscaling deployment, implement an `s3`/`r2` backend behind the existing
`StorageBackend` interface in `app/core/storage.py` so uploaded media is
shared and served from the CDN.

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `413 Request Entity Too Large` on upload | `client_max_body_size 105m` in `deploy/nginx.conf` is set to the default 100 MiB video cap; increase `MEDIA_MAX_VIDEO_SIZE_BYTES` and this value together. |
| `400 Invalid host header` | The `Host` header isn't in `TRUSTED_HOSTS`; add the domain (e.g. `api.beezents.com`). |
| Session cookie not sent/kept | `COOKIE_SECURE=true` requires HTTPS; make sure requests go through the TLS-terminating nginx/ALB, not straight to port 8000. |
| `/health` fails from an ALB/load balancer | Ensure the health-check path is `/health` and the target group points at the port nginx listens on (80/443) or at the API's 8000 if exposed. |
| Certificate not renewing | Confirm the `certbot` and `nginx` containers are running and the domain's A record still points at the instance; `docker compose -f docker-compose.prod.yml logs certbot` for errors. |
| API can't reach the database | Check RDS security group allows the EC2 security group on port 5432, and the `DATABASE_URL` is correct (the database must already exist). |