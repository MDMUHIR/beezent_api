# Beezents Backend — Remaining Development Roadmap & Strict Implementation Instructions

You are working on the **Beezents Backend**, the backend/API for a professional AI agency website that will later evolve into an AI-agent platform.

The backend is built with:

- FastAPI
- Python
- `uv` for dependency/project management
- PostgreSQL
- SQLAlchemy 2.x async
- asyncpg
- Alembic
- Pydantic v2
- pytest
- Ruff
- HTTP-only cookie authentication
- Argon2id password hashing

The project already has completed and verified:

- Phase 1 — FastAPI Foundation
- Phase 2 — PostgreSQL + SQLAlchemy + Alembic
- Phase 3 — Users + Authentication + RBAC
- Phase 4 — Core CMS Models
- Phase 5 — Public CMS API

The Phase 5 implementation has been independently verified against live PostgreSQL:

- 55 tests passing
- Ruff passing
- formatting passing
- Alembic checks passing
- live API endpoints verified
- published/unpublished content behavior verified
- pagination/filtering/search/sorting verified
- public response schema leakage checked

Phase 5 report:
`docs/phases/phase-05-public-cms-api.md`

The Phase 5 report states that the next phase should implement Admin CMS CRUD API and later Lead/File systems. Do not redo Phase 5 unless an actual regression is discovered.

---

# CRITICAL WORKING RULE

## DO NOT IMPLEMENT ALL PHASES AT ONCE

The roadmap below contains all remaining phases so you understand the final architecture.

However:

**Implement ONLY the CURRENT NEXT PHASE.**

After completing the current phase:

1. Debug it thoroughly.
2. Run the complete test suite.
3. Run static analysis.
4. Run formatting checks.
5. Run dependency/lock checks.
6. Run Alembic validation.
7. Test against real PostgreSQL.
8. Perform live API verification where applicable.
9. Check for security problems.
10. Check for regressions in previous phases.
11. Fix every issue discovered.
12. Re-run all relevant checks after fixes.
13. Create the permanent phase report.
14. Stop.

Do NOT automatically continue to the next phase.

The human developer will review the phase and then explicitly ask you to continue.

---

# MASTER DEVELOPMENT ROADMAP

Follow this sequence exactly:

```text
✅ Phase 1 — FastAPI Foundation
✅ Phase 2 — PostgreSQL + SQLAlchemy + Alembic
✅ Phase 3 — Users + Authentication + RBAC
✅ Phase 4 — Core CMS Models
✅ Phase 5 — Public CMS API

👉 Phase 6 — Admin CMS CRUD API
⬜ Phase 7 — Lead Management System
⬜ Phase 8 — File / Media Storage
⬜ Phase 9 — API Hardening & Security
⬜ Phase 10 — Testing & Quality Engineering
⬜ Phase 11 — Docker & Deployment
⬜ Phase 12 — Next.js Integration
⬜ Phase 13 — Future AI Platform Preparation
⬜ Phase 14 — Production Readiness
```

---

# GLOBAL ENGINEERING RULES FOR EVERY PHASE

These rules apply to EVERY remaining phase.

## 1. Do not overengineer

Prefer a clean modular monolith.

Do NOT introduce:

- microservices
- unnecessary repositories
- generic CRUD frameworks
- unnecessary service layers
- unnecessary dependency injection abstractions
- event buses
- CQRS
- complicated factories
- premature Redis
- Celery before actually needed
- LangChain/LangGraph before AI phase
- vector databases before AI/RAG phase

Use simple, explicit, maintainable FastAPI + SQLAlchemy code.

---

# 2. Preserve existing functionality

Never break:

- `/health`
- `/api/v1/health`
- `/api/v1/health/db`
- authentication
- registration
- login
- logout
- `/api/v1/auth/me`
- RBAC
- public CMS APIs
- database migrations
- existing tests

Before modifying existing code, understand how it currently works.

---

# 3. Database rules

Use:

- PostgreSQL
- SQLAlchemy 2.x typed mappings
- async sessions
- UUID primary keys
- timezone-aware timestamps
- explicit indexes
- explicit constraints
- PostgreSQL-specific features only when justified

Alembic is the **only source of truth for schema changes**.

Never manually modify the database schema as a replacement for migrations.

Every schema change must have an Alembic migration.

---

# 4. API rules

Use:

- FastAPI
- Pydantic v2
- explicit request schemas
- explicit response schemas
- proper HTTP status codes
- proper validation
- consistent error responses

Never return SQLAlchemy ORM objects directly when a response schema should be used.

Never expose:

- password hashes
- session tokens
- internal authentication fields
- unnecessary foreign keys
- sensitive database information

unless explicitly required.

---

# 5. Authentication and authorization

Use the existing authentication/RBAC implementation.

Admin endpoints must never rely only on frontend restrictions.

Authorization must be enforced server-side.

Use the existing:

```text
require_authenticated_user
require_staff
require_admin
```

where appropriate.

Never trust:

- request body role fields
- frontend role checks
- client-provided permissions
- hidden UI controls

---

# 6. Error handling

Every phase must consider:

- invalid input
- missing records
- duplicate records
- malformed requests
- unauthorized access
- forbidden access
- database failures
- transaction failures
- unexpected exceptions

Do not expose raw database errors to API clients.

Use safe, meaningful API errors.

---

# 7. Transaction safety

For write operations:

- validate first
- perform changes inside a transaction
- commit only when appropriate
- rollback safely on failures
- refresh objects when necessary
- avoid partially persisted state

Pay special attention to async SQLAlchemy behavior.

Avoid:

- `MissingGreenlet`
- detached ORM objects
- stale objects
- accidental implicit lazy loading
- uncommitted test data

---

# 8. Testing requirements

Every phase must include appropriate tests.

Use the real PostgreSQL test database where database behavior matters.

Do not replace database integration tests with mocks simply to make tests easier.

Tests should cover:

### Happy paths

### Validation failures

### Authorization failures

### Not-found cases

### Duplicate/conflict cases

### Edge cases

### Regression cases

### Database behavior

### Transaction behavior

### API response shape

### Security-sensitive behavior

When a bug is discovered during testing:

1. reproduce it
2. understand the root cause
3. fix the implementation
4. add a regression test
5. rerun the relevant test
6. rerun the full suite

Do not simply patch the symptom.

---

# 9. Mandatory debugging workflow

For every phase, follow this process:

```text
Implement
   ↓
Run targeted tests
   ↓
Debug failures
   ↓
Fix root causes
   ↓
Add regression tests
   ↓
Run complete test suite
   ↓
Run Ruff
   ↓
Run formatting check
   ↓
Run dependency/lock validation
   ↓
Run Alembic validation
   ↓
Run live PostgreSQL checks
   ↓
Review security
   ↓
Review regressions
   ↓
Create phase report
   ↓
Final verification
   ↓
STOP
```

Never declare a phase complete based only on code inspection.

---

# 10. Mandatory commands

Use `uv`, not pip.

Where applicable, run:

```bash
uv sync
uv lock --check
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run alembic check
uv run alembic current
uv run alembic upgrade head
```

If migrations changed, also test migration behavior carefully.

Where appropriate, run:

```bash
uv run alembic downgrade <previous_revision>
uv run alembic upgrade head
```

against the test database.

---

# 11. Permanent report requirement

EVERY phase MUST create or update a permanent report:

```text
docs/phases/phase-XX-<phase-name>.md
```

For example:

```text
docs/phases/phase-06-admin-cms-api.md
docs/phases/phase-07-leads.md
docs/phases/phase-08-file-storage.md
```

The report MUST be written after implementation and verification.

It must contain:

```text
# Phase X Report

## 1. Phase objective

## 2. Scope

## 3. Acceptance criteria

## 4. What was implemented

## 5. Files created

## 6. Files modified

## 7. Database changes

## 8. API endpoints

## 9. Authentication / authorization

## 10. Validation rules

## 11. Testing

## 12. Bugs discovered

## 13. Root causes

## 14. Fixes applied

## 15. Regression tests added

## 16. Security checks

## 17. Verification results

## 18. Known limitations

## 19. Architecture / design decisions

## 20. Deferred work

## 21. Next phase
```

IMPORTANT:

The report must describe what was **actually implemented and actually tested**.

Do NOT claim:

- tests passed if they were not run
- security was verified if it was not checked
- migration was tested if it was not tested
- deployment works if deployment was not tested

If something could not be verified, explicitly say:

```text
Not verified
```

and explain why.

---

# PHASE 6 — ADMIN CMS CRUD API

## Objective

Build the protected CMS administration API.

Use the existing:

```text
Project
Service
Solution
CaseStudy
```

models.

Use the existing admin-oriented schemas created during Phase 5.

Implement:

### Projects

```text
POST   /api/v1/admin/projects
GET    /api/v1/admin/projects
GET    /api/v1/admin/projects/{id}
PATCH  /api/v1/admin/projects/{id}
DELETE /api/v1/admin/projects/{id}
```

### Services

```text
POST   /api/v1/admin/services
GET    /api/v1/admin/services
GET    /api/v1/admin/services/{id}
PATCH  /api/v1/admin/services/{id}
DELETE /api/v1/admin/services/{id}
```

### Solutions

```text
POST   /api/v1/admin/solutions
GET    /api/v1/admin/solutions
GET    /api/v1/admin/solutions/{id}
PATCH  /api/v1/admin/solutions/{id}
DELETE /api/v1/admin/solutions/{id}
```

### Case studies

```text
POST   /api/v1/admin/case-studies
GET    /api/v1/admin/case-studies
GET    /api/v1/admin/case-studies/{id}
PATCH  /api/v1/admin/case-studies/{id}
DELETE /api/v1/admin/case-studies/{id}
```

Requirements:

- protected with appropriate RBAC
- staff/admin access only where appropriate
- validate duplicate slugs
- return `409 Conflict` for slug conflicts
- support partial updates
- validate foreign keys
- validate malformed UUIDs
- handle nonexistent resources with `404`
- safely handle deletion
- preserve public API behavior
- never allow a normal user to access admin APIs

Test:

```text
user → forbidden
client → forbidden unless explicitly permitted
staff → correct permissions
admin → full permissions
unauthenticated → unauthorized
```

Do not add Lead/File/AI functionality in this phase.

Create:

```text
docs/phases/phase-06-admin-cms-api.md
```

Then stop.

---

# PHASE 7 — LEAD MANAGEMENT SYSTEM

## Objective

Create a secure lead/contact submission system for the marketing website.

Create a `Lead` model.

Suggested information:

```text
id
name
email
phone
company
service
message
source
status
notes
created_at
updated_at
```

Use an appropriate enum for lead status, for example:

```text
new
contacted
qualified
converted
lost
```

Public endpoint:

```text
POST /api/v1/leads
```

Admin endpoints:

```text
GET    /api/v1/admin/leads
GET    /api/v1/admin/leads/{id}
PATCH  /api/v1/admin/leads/{id}
DELETE /api/v1/admin/leads/{id}
```

Requirements:

- strict validation
- email validation
- reasonable length limits
- safe optional fields
- no public access to other leads
- admin/staff authorization
- pagination for admin list
- filtering by status
- sorting
- search
- safe error handling
- database migration
- tests

Consider basic anti-spam protections at the API design level, but do not introduce Redis unless truly required.

Do not implement email sending yet.

Create:

```text
docs/phases/phase-07-leads.md
```

Then stop.

---

# PHASE 8 — FILE / MEDIA STORAGE

## Objective

Create a clean abstraction for website media.

Do NOT store image binaries directly in PostgreSQL.

Design for object storage such as:

```text
Cloudflare R2
S3-compatible storage
```

The database should store metadata/reference information.

Create an appropriate `File` or `Media` model.

Potential fields:

```text
id
original_name
storage_key
public_url
mime_type
size
width
height
alt_text
folder
uploaded_by
created_at
updated_at
```

Requirements:

- secure filename handling
- MIME validation
- size validation
- UUID-based storage naming
- no arbitrary filesystem paths from users
- ownership/uploader tracking
- admin authorization
- metadata storage
- clean storage abstraction

If actual R2/S3 credentials are not available, create a testable storage interface and local development adapter.

Do NOT hard-code cloud credentials.

Do NOT commit secrets.

Create:

```text
docs/phases/phase-08-file-storage.md
```

Then stop.

---

# PHASE 9 — API HARDENING & SECURITY

## Objective

Audit and harden the backend before frontend integration.

Review:

### Authentication

- session expiration
- cookie flags
- logout behavior
- invalid session handling
- secure cookie configuration
- production configuration

### Authorization

Verify every protected endpoint.

Check for:

- privilege escalation
- IDOR
- role bypass
- unauthorized object access

### Validation

Check:

- maximum lengths
- malformed UUIDs
- malformed JSON
- unexpected fields
- dangerous values

### API security

Review:

- CORS
- trusted hosts
- security headers
- error leakage
- SQL injection safety
- path traversal
- file upload security
- mass assignment

### Authentication abuse

Consider:

- login brute-force protection
- registration abuse
- lead spam
- request throttling

Only introduce Redis/rate limiting if justified.

### Secrets

Search the project for accidentally committed:

```text
API keys
passwords
database URLs
tokens
secret keys
```

Check `.env`, `.gitignore`, and configuration behavior.

Create:

```text
docs/phases/phase-09-api-hardening.md
```

Include an explicit security audit checklist and findings.

Then stop.

---

# PHASE 10 — TESTING & QUALITY ENGINEERING

## Objective

Perform a comprehensive quality pass over the entire backend.

Do not primarily add features.

Focus on correctness.

Review:

```text
unit tests
integration tests
API tests
database tests
authentication tests
authorization tests
CMS tests
lead tests
file tests
migration tests
```

Add missing tests.

Ensure tests cover:

- success
- validation
- unauthorized
- forbidden
- not found
- conflicts
- pagination
- filtering
- sorting
- edge cases
- database constraints
- transactions
- regression bugs

Run the entire test suite.

Target:

```text
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run alembic check
```

Fix all real issues discovered.

Do not suppress Ruff warnings merely to obtain a green result unless the suppression is justified.

Create:

```text
docs/phases/phase-10-testing-quality.md
```

Include a quality audit.

Then stop.

---

# PHASE 11 — DOCKER & DEPLOYMENT

## Objective

Prepare the backend for reliable deployment.

Create production-oriented Docker configuration.

Requirements:

- multi-stage Docker build where appropriate
- minimal runtime image
- non-root user where practical
- environment-based configuration
- no secrets in image
- health check
- proper Uvicorn/Gunicorn strategy where appropriate
- PostgreSQL externalized
- graceful startup
- graceful shutdown

Create appropriate:

```text
Dockerfile
.dockerignore
docker-compose.yml
```

only if useful for local development.

Do not unnecessarily containerize PostgreSQL for production.

Document environment variables.

Test the Docker image locally.

Verify:

```text
build
startup
health endpoint
database connection
migration behavior
API availability
```

Create:

```text
docs/phases/phase-11-docker-deployment.md
```

Then stop.

---

# PHASE 12 — NEXT.JS INTEGRATION

## Objective

Prepare the backend for the Next.js marketing frontend.

Do NOT build the entire frontend here unless explicitly requested.

Ensure the backend provides clean frontend-consumable APIs.

Review:

- CORS
- API base URL configuration
- cookies
- authentication flow
- public CMS APIs
- admin APIs
- lead submission
- media URLs
- pagination
- error formats

Document frontend integration patterns.

Test actual requests from a Next.js development environment where possible.

Make sure frontend developers do not need direct database access.

Create:

```text
docs/phases/phase-12-nextjs-integration.md
```

Then stop.

---

# PHASE 13 — FUTURE AI PLATFORM PREPARATION

## IMPORTANT

This phase is preparation only.

Do NOT implement a full AI-agent system yet.

Prepare the backend architecture so future AI functionality can be added without rewriting the application.

Potential future concepts:

```text
Agent
Conversation
Message
AgentRun
Tool
KnowledgeDocument
KnowledgeChunk
Embedding
```

But do NOT create unnecessary tables simply because they may be useful.

First determine what is actually needed.

Prepare clean extension points for:

```text
AI agents
RAG
conversation history
agent runs
streaming
background jobs
LLM providers
tool execution
```

Future technologies may include:

```text
LangGraph
LangChain
Redis
Celery
pgvector
object storage
```

But do not add them unless there is a concrete requirement in this phase.

The goal is:

```text
Current Website Backend
        ↓
Future AI Platform
```

without creating unnecessary complexity today.

Create:

```text
docs/phases/phase-13-future-ai-preparation.md
```

Then stop.

---

# PHASE 14 — PRODUCTION READINESS

## Objective

Perform the final backend production-readiness audit.

This is NOT primarily a feature phase.

Review the entire backend.

Check:

### Architecture

- project structure
- dependencies
- unnecessary abstractions
- circular dependencies
- configuration

### Database

- migrations
- indexes
- constraints
- transaction behavior
- connection pooling

### Authentication

- password hashing
- sessions
- cookies
- expiration
- logout
- RBAC

### API

- validation
- errors
- pagination
- filtering
- security
- CORS

### Testing

- full test suite
- regression tests
- integration tests

### Performance

Check obvious issues such as:

- N+1 queries
- unnecessary database queries
- inefficient pagination
- missing indexes
- unnecessary serialization

Do not prematurely optimize without evidence.

### Observability

Ensure useful:

- structured logging
- error logging
- request information
- database failure logging

without logging secrets or sensitive information.

### Deployment

Verify:

- Docker
- environment variables
- health checks
- migrations
- startup
- shutdown

### Documentation

Review:

```text
README.md
API documentation
environment variables
development setup
deployment setup
architecture documentation
phase reports
```

Create a final production-readiness report:

```text
docs/phases/phase-14-production-readiness.md
```

The report must clearly separate:

```text
READY
NEEDS ATTENTION
NOT IMPLEMENTED
DEFERRED
```

Do not claim production-ready if critical issues remain.

Then stop.

---

# FINAL QUALITY STANDARD

At the end of EVERY phase, answer these questions internally before declaring completion:

### Functionality

- Does the requested functionality actually work?

### Regression

- Did anything from previous phases break?

### Security

- Can unauthorized users access it?
- Can users escalate privileges?
- Is sensitive information exposed?

### Database

- Are constraints correct?
- Are migrations correct?
- Are transactions safe?

### API

- Are status codes correct?
- Are schemas correct?
- Are errors safe?

### Testing

- Is there a test for every important bug discovered?
- Does the complete suite pass?

### Code quality

- Does Ruff pass?
- Does formatting pass?
- Is the code understandable?

### Deployment

- Will this work in a production environment?
- Are secrets handled correctly?

### Documentation

- Is the permanent phase report complete?
- Does it describe only work that was actually performed?

---

# ABSOLUTE STOP CONDITION

After completing the current phase:

**STOP.**

Do not begin the next phase automatically.

Return a concise terminal summary containing:

```text
PHASE: X
STATUS: COMPLETE / BLOCKED

Implemented:
- ...

Tests:
- ...

Quality:
- ...

Database:
- ...

Security:
- ...

Bugs found:
- ...

Bugs fixed:
- ...

Report:
docs/phases/phase-XX-....md

Next phase:
Phase X+1
```

Only proceed to the next phase when the developer explicitly asks you to.


<!-- Before changing code, inspect the existing Phase 1–5 implementation and tests so that the new implementation follows the project's existing conventions. -->

