# 🚀 FastAPI Agency Backend & SQLAdmin CMS

A production-ready, high-performance **FastAPI (Python 3.11+)** backend and **SQLAdmin CMS** engine designed for modern agency websites (similar to Riseup Labs). Engineered with **SQLAlchemy 2.0 (Async)**, **PostgreSQL**, **Pydantic v2**, and **OAuth2 JWT Bearer RBAC**.

---

## 📑 Table of Contents

1. [Architecture & Features](#-architecture--features)
2. [Project File Structure](#-project-file-structure)
3. [Environment Configuration (.env)](#-environment-configuration-env)
4. [Running on Localhost](#-running-on-localhost)
   - [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
   - [Option B: Native Python Virtual Environment](#option-b-native-python-virtual-environment)
5. [Running & Connecting Remotely](#-running--connecting-remotely)
   - [1. Remote PostgreSQL Connection](#1-remote-postgresql-connection)
   - [2. SSH Port Forwarding (Access Remote Backend Locally)](#2-ssh-port-forwarding)
   - [3. Secure Public Tunneling (Cloudflare Tunnels / ngrok)](#3-secure-public-tunneling)
6. [Deploying to Production / Live Server](#-deploying-to-production--live-server)
   - [1. Production VPS (Ubuntu / Debian / AWS EC2 / DigitalOcean)](#1-production-vps-deployment)
   - [2. Nginx Reverse Proxy with SSL (Let's Encrypt / Certbot)](#2-nginx-reverse-proxy-with-ssl)
   - [3. Systemd Service (Non-Docker Production)](#3-systemd-service-setup)
   - [4. Cloud Container Platforms (Google Cloud Run, AWS App Runner, Render)](#4-cloud-container-platforms)
7. [Database Migrations (Alembic)](#-database-migrations-alembic)
8. [Database Seeding & Default Credentials](#-database-seeding--default-credentials)
9. [Full REST API Documentation](#-full-rest-api-documentation)
10. [SQLAdmin CMS Guide](#-sqladmin-cms-guide)
11. [Frontend Integration Examples (Next.js 14 / Nuxt 3)](#-frontend-integration-examples)
12. [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## 🏛 Architecture & Features

- **FastAPI 0.110+**: Asynchronous request handling with OpenAPI 3.1 interactive Swagger docs (`/api/v1/docs`).
- **Dual-Engine SQLAlchemy 2.0**:
  - `AsyncEngine` + `asyncpg` for high-throughput asynchronous REST API handlers.
  - `SyncEngine` + `psycopg2` for SQLAdmin and Alembic schema migrations.
- **SQLAdmin CMS**: Administrative dashboard mounted at `/admin` with session cookie authentication and RBAC.
- **Role-Based Access Control (RBAC)**: `SUPER_ADMIN`, `ADMIN`, `EDITOR` roles enforced via FastAPI dependency injection.
- **Comprehensive Agency Domain Models**:
  - **Services & Stacks**: Categories, markdown service detail pages, tech stacks with Many-to-Many associations.
  - **Portfolio & Case Studies**: Quantifiable metrics (`99.4% Accuracy`, `$4.2M Saved`), client profiles, industries.
  - **Staff Augmentation**: Talent roster, seniority, hourly rates, availability timelines.
  - **Inbound CRM Leads**: Contact form submissions with status workflow (`NEW` $\rightarrow$ `CONTACTED` $\rightarrow$ `CLOSED`).
  - **Careers & Recruitment**: Job postings, salary bands, applicant CV tracking.
  - **Social Proof**: Testimonials with star ratings, press coverage, live company statistics.

---

## 📂 Project File Structure

```
backend/
├── app/
│   ├── admin/                         # SQLAdmin CMS configuration & Auth
│   │   ├── __init__.py                # setup_admin(app, engine)
│   │   ├── auth.py                    # AdminAuth session middleware
│   │   └── views.py                   # ModelView definitions with search & filters
│   ├── api/                           # FastAPI route handlers & dependencies
│   │   ├── __init__.py
│   │   ├── deps.py                    # JWT Bearer, RBAC role checkers & DB injectors
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py                 # Master v1 router aggregating all endpoints
│   │       └── endpoints/
│   │           ├── auth.py            # Login, /me, user management
│   │           ├── careers.py         # Job postings & candidate applications
│   │           ├── case_studies.py    # Portfolio, industries & metrics
│   │           ├── inquiries.py       # Contact leads & CRM status
│   │           ├── services.py        # Service categories, services & tech stacks
│   │           ├── social_proof.py    # Testimonials, press & stats
│   │           └── talent.py          # Staff augmentation & talent profiles
│   ├── core/                          # Core configuration & security
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic Settings (.env configuration & CORS)
│   │   ├── database.py                # AsyncSession for FastAPI + sync engine for SQLAdmin
│   │   └── security.py                # CryptContext bcrypt hashing & JWT tokens
│   ├── models/                        # SQLAlchemy 2.0 Declarative ORM models
│   │   ├── __init__.py
│   │   ├── base.py                    # Base & TimestampMixin (created_at, updated_at)
│   │   ├── career.py                  # JobPosting & JobApplication models
│   │   ├── case_study.py              # Industry, CaseStudy, CaseStudyMetric models
│   │   ├── inquiry.py                 # ContactInquiry model & InquiryStatus Enum
│   │   ├── service.py                 # ServiceCategory, Service, TechStack & M2M table
│   │   ├── social_proof.py            # Testimonial, PressCoverage & CompanyStat
│   │   ├── talent.py                  # TalentRole augmentation profile model
│   │   └── user.py                    # User model & UserRole Enum
│   └── schemas/                       # Pydantic v2 validation models
│       ├── __init__.py
│       ├── career.py
│       ├── case_study.py
│       ├── inquiry.py
│       ├── service.py
│       ├── social_proof.py
│       ├── talent.py
│       └── user.py
├── alembic/                           # Database migration scripts
│   ├── env.py                         # Async & sync Alembic migration runner
│   ├── script.py.mako
│   └── versions/
├── .env.example                       # Default environment variables
├── alembic.ini                        # Alembic configuration
├── docker-compose.yml                 # Multi-container PostgreSQL 16 + FastAPI
├── Dockerfile                         # Python 3.11-slim production container
├── main.py                            # FastAPI app, CORS, SessionMiddleware & SQLAdmin
├── requirements.txt                   # Production pinned dependencies
├── seed.py                            # Super-admin (admin@agency.com) & demo data seeder
└── README.md                          # Full documentation manual
```

---

## ⚙️ Environment Configuration (.env)

Create a `.env` file in the `backend/` root:

```bash
# App Settings
PROJECT_NAME="FastAPI Agency Engine"
API_V1_STR="/api/v1"
SECRET_KEY="generate-a-secure-random-64-character-key-here"
ADMIN_SESSION_SECRET="generate-another-secure-random-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 Hours

# Database Settings (Local / Docker)
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=agency_db

# CORS Allowed Origins (Comma-separated for multiple frontend domains)
BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:3001,https://youragency.com,https://admin.youragency.com"
```

To generate cryptographic secret keys on Linux/macOS:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 💻 Running on Localhost

### Option A: Docker Compose (Recommended)

Requires [Docker](https://docs.docker.com/get-docker/) & Docker Compose.

1. **Clone or Extract the project:**
   ```bash
   cd backend/
   ```

2. **Create the environment file from the template:**
   ```bash
   cp .env.example .env
   ```

3. **Start the complete stack:**
   ```bash
   docker compose up -d --build
   ```

4. **Check container logs:**
   ```bash
   docker compose logs -f api
   ```

5. **Access the services:**
   - **FastAPI OpenAPI Swagger Docs:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - **ReDoc Documentation:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
   - **SQLAdmin CMS Portal:** [http://localhost:8000/admin](http://localhost:8000/admin)
   - **PostgreSQL Database:** `localhost:5432` (`postgres:postgres`)

> **Note:** If you are not a member of the `docker` group, prefix commands with `sudo` or add your user:
> ```bash
> sudo usermod -aG docker $USER && newgrp docker
> ```

---

### Option B: Native Python Virtual Environment

#### 1. Prerequisites
- Python 3.11 or 3.12
- PostgreSQL 15 or 16 running locally

#### 2. Setup PostgreSQL Database
```sql
-- In psql or pgAdmin:
CREATE DATABASE agency_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE agency_db TO postgres;
```

#### 3. Setup Virtualenv and Run
```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
# On Linux / macOS:
source venv/bin/activate
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment (database, secrets, CORS)
cp .env.example .env

# 5. Run database migrations (or use auto-create tables via lifespan)
alembic upgrade head

# 6. Seed initial super-admin and demo agency records
python seed.py

# 7. Run the test suite
pytest

# 8. Start the FastAPI development server with Hot Reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 Running & Connecting Remotely

### 1. Remote PostgreSQL Connection
If your database is hosted on Supabase, Neon, AWS RDS, or a remote server, update `.env`:
```bash
POSTGRES_SERVER=db.your-region.supabase.co
POSTGRES_PORT=5432
POSTGRES_USER=postgres.youruser
POSTGRES_PASSWORD=your_strong_remote_password
POSTGRES_DB=postgres
```
The database adapter automatically builds:
- Async: `postgresql+asyncpg://user:pass@host:port/db`
- Sync: `postgresql+psycopg2://user:pass@host:port/db`

---

### 2. SSH Port Forwarding
If the backend is running on a remote cloud VM (e.g. AWS EC2 at `203.0.113.50`), you can securely forward port 8000 to your local machine without opening firewall ports:

```bash
# Forward remote port 8000 to local localhost:8000
ssh -N -L 8000:localhost:8000 ubuntu@203.0.113.50 -i ~/.ssh/id_rsa
```
Now browse to `http://localhost:8000/api/v1/docs` in your local browser!

---

### 3. Secure Public Tunneling (Cloudflare Tunnels / ngrok)

#### Using Cloudflare Tunnel (Free & Production-Ready):
```bash
# Install cloudflared and start tunnel
cloudflared tunnel --url http://localhost:8000
```
This generates a secure URL like `https://random-subdomain.trycloudflare.com` accessible anywhere globally.

#### Using ngrok:
```bash
ngrok http 8000
```

---

## 🚀 Deploying to Production / Live Server

### 1. Production VPS Deployment (Ubuntu / Debian)

#### Step 1: Provision Server & Install Docker
```bash
# Update OS packages
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### Step 2: Clone Code & Configure Production `.env`
```bash
mkdir -p /opt/agency-backend
cd /opt/agency-backend
# Copy backend files here
cp .env.example .env
nano .env  # Enter strong SECRET_KEY and production domain
```

#### Step 3: Run with Docker Compose
```bash
docker-compose up -d --build
```

---

### 2. Nginx Reverse Proxy with SSL (Let's Encrypt / Certbot)

Install Nginx and Certbot on your host:
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create Nginx site configuration: `/etc/nginx/sites-available/api.youragency.com`
```nginx
server {
    server_name api.youragency.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site & provision SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/api.youragency.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Obtain free SSL cert with auto-renewal
sudo certbot --nginx -d api.youragency.com
```

---

### 3. Systemd Service Setup (Non-Docker Production)

If running directly on the host using Python venv:

Create service file: `/etc/systemd/system/fastapi-agency.service`
```ini
[Unit]
Description=FastAPI Agency Engine & SQLAdmin
After=network.target postgresql.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/agency-backend
Environment="PATH=/opt/agency-backend/venv/bin"
EnvironmentFile=/opt/agency-backend/.env
ExecStart=/opt/agency-backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi-agency
sudo systemctl start fastapi-agency
sudo systemctl status fastapi-agency
```

---

### 4. Cloud Container Platforms

#### Deploying to Google Cloud Run:
```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID

# Build and deploy container
gcloud run deploy agency-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars="POSTGRES_SERVER=YOUR_CLOUD_SQL_IP,POSTGRES_PASSWORD=YOUR_DB_PASS,SECRET_KEY=YOUR_KEY"
```

#### Deploying to Render / Railway:
- Set Build Command: `pip install -r requirements.txt && python seed.py`
- Set Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add PostgreSQL Database service and bind environment variables.

---

## 🗄 Database Migrations (Alembic)

Alembic manages incremental schema changes without data loss.

| Action | Command |
|---|---|
| **Apply All Migrations** | `alembic upgrade head` |
| **Generate New Migration** | `alembic revision --autogenerate -m "add_column_name"` |
| **Rollback 1 Migration** | `alembic downgrade -1` |
| **View Migration History** | `alembic history --verbose` |
| **View Current Version** | `alembic current` |

---

## 👤 Database Seeding & Default Credentials

Run the database seeder to initialize tables, create default user roles, and populate realistic agency showcase records:

```bash
python seed.py
```

### Default Credentials:

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Super Admin** | `admin@agency.com` | `admin123` | Full SQLAdmin CMS + All Write/Delete Endpoints |
| **Editor** | `editor@agency.com` | `editor123` | Content CRUD (Services, Case Studies, Testimonials) |

---

## 📡 Full REST API Documentation

### 1. Authentication & Users (`/api/v1/auth`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Public | Authenticate with email/password; returns JWT Bearer token |
| `GET` | `/api/v1/auth/me` | Authenticated | Get current authenticated user profile and role |
| `GET` | `/api/v1/auth/users` | Admin+ | List all administrative staff |
| `POST` | `/api/v1/auth/users` | Super Admin | Create new staff user with designated role |

#### Login Request Example:
```json
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@agency.com",
  "password": "admin123"
}
```
#### Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@agency.com",
    "full_name": "Agency Super Admin",
    "role": "SUPER_ADMIN",
    "is_active": true
  }
}
```

---

### 2. Services & Technology Stacks (`/api/v1/services`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/services/categories` | Public | List categories with nested services & tech stacks (Mega-menu) |
| `GET` | `/api/v1/services/` | Public | List all active services (filterable by `category_slug`, `featured`) |
| `GET` | `/api/v1/services/{slug}` | Public | Get full service detail page by slug |
| `POST` | `/api/v1/services/` | Editor+ | Create a new service offering |
| `PUT` | `/api/v1/services/{id}` | Editor+ | Update existing service |
| `DELETE` | `/api/v1/services/{id}` | Admin+ | Delete service |
| `GET` | `/api/v1/services/tech-stacks/all` | Public | List all technology stacks categorized by domain |

---

### 3. Portfolio & Case Studies (`/api/v1/case-studies`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/case-studies/` | Public | List published case studies with client info and metrics |
| `GET` | `/api/v1/case-studies/{slug}` | Public | Get single case study by slug with full challenge/solution breakdown |
| `POST` | `/api/v1/case-studies/` | Editor+ | Create new case study |
| `PUT` | `/api/v1/case-studies/{id}` | Editor+ | Update case study |
| `DELETE` | `/api/v1/case-studies/{id}` | Admin+ | Delete case study |
| `GET` | `/api/v1/case-studies/industries/all` | Public | List all industry domains |

---

### 4. Staff Augmentation & Talent (`/api/v1/talent`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/talent/` | Public | List talent profiles with skills, hourly rates, and availability |
| `GET` | `/api/v1/talent/{slug}` | Public | Get talent role profile by slug |
| `POST` | `/api/v1/talent/` | Editor+ | Create talent role |

---

### 5. Inbound CRM Inquiries (`/api/v1/inquiries`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/inquiries/` | Public | Submit contact / project lead inquiry |
| `GET` | `/api/v1/inquiries/` | Admin+ | List inquiries (filter by `status`: `NEW`, `CONTACTED`, etc.) |
| `PATCH` | `/api/v1/inquiries/{id}/status` | Admin+ | Update CRM status and add internal admin notes |

---

### 6. Careers & Job Applications (`/api/v1/careers`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/careers/jobs` | Public | List active job postings |
| `GET` | `/api/v1/careers/jobs/{slug}` | Public | Get single job posting details |
| `POST` | `/api/v1/careers/jobs/{id}/apply` | Public | Submit candidate application & CV URL |
| `GET` | `/api/v1/careers/applications` | Admin+ | List candidate applications with status |

---

### 7. Social Proof & Media (`/api/v1/social-proof`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/social-proof/testimonials` | Public | Verified client testimonials |
| `GET` | `/api/v1/social-proof/press` | Public | Press & media articles |
| `GET` | `/api/v1/social-proof/stats` | Public | Quantifiable agency milestone numbers |

---

## 🛡 SQLAdmin CMS Guide

SQLAdmin provides an administrative interface directly inside FastAPI:

- **URL:** [http://localhost:8000/admin](http://localhost:8000/admin)
- **Authentication:** Custom `AdminAuth` backend using signed session cookies.
- **Features:**
  - Full CRUD operations on all 14 database models.
  - Search fields and column sorting.
  - Inline foreign key relation inspection.
  - RBAC protection (only `SUPER_ADMIN` and `ADMIN` roles can log in).

---

## ⚡ Frontend Integration Examples

### Next.js 14 (App Router) Server Component

```tsx
// app/services/page.tsx
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Engineering Capabilities | Agency',
};

interface ServiceCategory {
  id: number;
  name: string;
  slug: string;
  services: Array<{
    id: number;
    title: string;
    slug: string;
    short_description: string;
    icon_url: string;
    tech_stacks: string[];
  }>;
}

export async function getServices(): Promise<ServiceCategory[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/services/categories`, {
    next: { revalidate: 60 }, // ISR Cache for 60 seconds
  });
  if (!res.ok) throw new Error('Failed to fetch services');
  return res.json();
}

export default async function ServicesPage() {
  const categories = await getServices();

  return (
    <main className="max-w-7xl mx-auto py-16 px-6">
      <h1 className="text-4xl font-extrabold tracking-tight">Our Core Services</h1>
      <div className="space-y-16 mt-12">
        {categories.map((cat) => (
          <section key={cat.id}>
            <h2 className="text-2xl font-bold text-slate-900">{cat.name}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              {cat.services.map((service) => (
                <article key={service.id} className="p-6 rounded-2xl border border-slate-200 hover:shadow-lg transition">
                  <h3 className="text-xl font-semibold">{service.title}</h3>
                  <p className="text-slate-600 mt-2 text-sm">{service.short_description}</p>
                  <div className="flex flex-wrap gap-1.5 mt-4">
                    {service.tech_stacks.map((tech) => (
                      <span key={tech} className="px-2 py-0.5 text-xs bg-slate-100 rounded text-slate-700 font-mono">
                        {tech}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
```

---

### Inbound Contact Lead Submission (React / Nuxt / Next.js)

```ts
// Submit lead to FastAPI backend
export async function submitContactLead(formData: {
  full_name: string;
  email: string;
  company_name?: string;
  service_interest: string;
  budget_range: string;
  message: string;
}) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/inquiries/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Inquiry submission failed');
  }

  return response.json();
}
```

---

## ❓ Troubleshooting & FAQ

#### 1. CORS Error when calling API from Frontend:
Check `BACKEND_CORS_ORIGINS` in your `.env` file. Ensure your frontend origin (e.g., `http://localhost:3000`) is included without a trailing slash. The value may be a JSON array (`["http://localhost:3000"]`) or a comma-separated string.

#### 2. Database connection refused (`asyncpg.exceptions.ConnectionDoesNotExistError`):
Verify PostgreSQL is active and listening on port 5432:
```bash
sudo systemctl status postgresql
# Or with Docker:
docker compose ps
```

#### 3. Alembic `Target database is not up to date`:
Run `alembic upgrade head` to apply all pending schema revisions.

#### 4. Container restarts with `ValueError: password cannot be longer than 72 bytes` or `AttributeError: module 'bcrypt' has no attribute '__about__'`:
This is a `passlib`/`bcrypt` version incompatibility. `requirements.txt` pins `bcrypt==4.0.1` which is compatible with `passlib 1.7.4`. Rebuild the image to apply:
```bash
docker compose up -d --build
```

#### 5. Swagger "Authorize" button fails to login:
The OAuth2 token endpoint is `/api/v1/auth/login-form` (form-encoded). The JSON login is `/api/v1/auth/login`. Swagger UI is pre-configured correctly.

#### 6. Permission denied on Docker socket:
```bash
sudo usermod -aG docker $USER && newgrp docker
```

#### 7. SQLAdmin `/admin` logs in but redirects back to the login page:
The authentication backend must return `True` (not `None`) from `authenticate()` — SQLAdmin treats a falsy return as a failed login. Ensure `app/admin/auth.py` returns `True` on success, then restart the container:
```bash
docker compose restart api
```

---

## 📜 License

MIT License. Engineered for agency production infrastructure.
