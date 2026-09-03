# Phase 9 Report — API Hardening & Security

**Project:** Beezents Backend
**Phase scope:** Security audit and hardening of the API before frontend integration
**Date:** 2026-09-03
**Status:** Complete and verified against a live PostgreSQL instance

---

## 1. Phase objective

Audit and harden the backend across authentication, authorization, validation,
API security, abuse protection, and secrets management. Fix real issues found,
add regression tests, and produce an explicit security audit checklist with
findings. Rate limiting/Redis is only introduced if justified (it is not — see
§18/§22).

## 2. Scope

- Authentication: session expiration, cookie flags, logout, invalid-session
  handling, production configuration.
- Authorization: every protected endpoint, privilege escalation, IDOR, role
  bypass, unauthorized object access.
- Validation: max lengths, malformed UUIDs/JSON, unexpected fields, dangerous
  values.
- API security: CORS, trusted hosts, security headers, error leakage, SQL
  injection, path traversal, file upload security, mass assignment.
- Abuse: login brute-force, registration abuse, lead spam, throttling.
- Secrets: scan for committed credentials/keys/tokens/URLs.

Out of scope: Redis/rate limiting (deferred), CAPTCHA, OAuth, MFA, TLS
termination (deployment-layer).

## 3. Acceptance criteria

| Criterion | Status |
| --- | --- |
| Security headers on responses | ✅ (ASGI middleware + 500 handler) |
| Configurable CORS (disabled by default) | ✅ |
| Configurable trusted-host validation (disabled by default) | ✅ |
| Malformed JSON / validation errors → safe 422 | ✅ |
| Unexpected 500s → safe JSON `{"detail": "Internal Server Error"}` | ✅ |
| Logout clears the browser cookie | ✅ (bug fixed) |
| Expired/invalid sessions rejected | ✅ (tested) |
| Mass-assignment protection re-verified | ✅ |
| Secrets scan clean | ✅ (no committed credentials) |
| No raw SQL interpolation | ✅ |
| Full suite passes, no regressions | ✅ 226 passed |
| Security audit checklist + findings | ✅ §22 |
| README + `.env.example` updated | ✅ |
| Phase report created | ✅ |

## 4. What was implemented

- **`SecurityHeadersMiddleware`** (`app/core/middleware.py`, pure ASGI): adds
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`
  to every HTTP response. Pure ASGI (not `BaseHTTPMiddleware`) so headers apply
  broadly.
- **Config-driven CORS** (`app/core/config.py`, `app/main.py`): when
  `CORS_ALLOWED_ORIGINS` is set, `CORSMiddleware` is enabled with
  `allow_credentials=True`, all methods/headers. Empty (default) = CORS
  disabled.
- **Config-driven trusted hosts** (`app/core/config.py`, `app/main.py`): when
  `TRUSTED_HOSTS` is set, `TrustedHostMiddleware` rejects other Host headers
  with `400`. Empty (default) = disabled (dev).
- **Safe global exception handler** (`app/main.py`): logs the exception
  server-side (method + path only, no PII) and returns a JSON `500`
  `{"detail": "Internal Server Error"}` with no internals leaked. Because
  FastAPI routes the `Exception` handler to Starlette's outermost
  ServerErrorMiddleware (whose response bypasses the app middleware stack), the
  security headers are also applied explicitly in the handler.
- **Logout cookie-clear bug fix** (`app/api/v1/endpoints/auth.py`): the logout
  endpoint now returns the mutated response (with the expired-cookie `Set-Cookie`)
  instead of a brand-new `Response`, so browsers actually drop the cookie.
- **Tests** (`tests/test_security.py`, 15 tests): security headers (success +
  error responses), CORS (allowed/disallowed/preflight), trusted hosts
  (accept/reject), malformed JSON, unexpected fields, safe 500, safe validation
  errors, cookie flags, invalid token, expired session + cleanup, logout cookie
  clearing.

## 5. Files created

| File | Purpose |
| --- | --- |
| `app/core/middleware.py` | `SecurityHeadersMiddleware` + header map |
| `tests/test_security.py` | 15 security tests |
| `docs/phases/phase-09-api-hardening.md` | This report |

## 6. Files modified

| File | Change |
| --- | --- |
| `app/core/config.py` | Added `cors_allowed_origins`, `trusted_hosts` settings |
| `app/main.py` | CORS + TrustedHost middleware (config-driven), SecurityHeaders middleware, safe 500 exception handler |
| `app/api/v1/endpoints/auth.py` | Logout now returns the mutated response (cookie clear actually sent) |
| `tests/conftest.py` | Enables CORS + trusted hosts in the test app (`testserver` allowed) |
| `.env.example` | Documented `CORS_ALLOWED_ORIGINS`, `TRUSTED_HOSTS` |
| `README.md` | "API security / hardening" section + configuration + known gaps |

No new dependencies. Lockfile unchanged (44 packages).

## 7. Database changes

**None.** `alembic check` reports no pending operations; revision stays at
`147c3d1fc707 (head)`. No schema changes were needed for this hardening phase.

## 8. API endpoints

No endpoints were added or removed. Endpoint inventory was audited (see §22):
public (`/health*`, `/auth/register`, `/auth/login`, `/auth/logout`, public CMS,
`POST /leads`), authenticated (`/auth/me`), staff-only (`/admin/*`), and dev
role-check endpoints (`/dev/*`).

## 9. Authentication / authorization

- Session cookie: `HttpOnly`, `SameSite=lax`, `Path=/`, `Secure` when
  `COOKIE_SECURE=true` (dev default `false`).
- Session lifetime: `SESSION_MAX_AGE_SECONDS` (7 days). Expired sessions are
  rejected with `401` and the row is deleted server-side (`get_current_user`).
- Invalid/unknown session tokens → `401`.
- Logout deletes the server-side session row **and** now clears the browser
  cookie (fixed).
- Authorization: every `/admin/*` route uses `require_staff`; `/auth/me` uses
  `get_current_user`. No privilege-escalation or role-bypass path found (see
  §22).

## 10. Validation rules

Re-audited (no changes): all input schemas enforce max lengths; slugs/emails/
folder names are normalized/validated; malformed UUIDs → 422; malformed JSON →
422 with a safe body; oversized uploads → 413; unexpected/extra fields are
ignored by Pydantic (safe because models are constructed from explicit
whitelisted fields only).

## 11. Testing

### `tests/test_security.py` (15 tests)

| Test | Verifies |
| --- | --- |
| `test_security_headers_present_on_success` | Headers on a normal response |
| `test_security_headers_present_on_errors` | Headers on a 404 response |
| `test_cors_allowed_origin` | Allowed origin → `Access-Control-Allow-Origin` + credentials |
| `test_cors_disallowed_origin` | Unknown origin → no ACAO header |
| `test_cors_preflight_allowed` | OPTIONS preflight → 200 + ACAO |
| `test_untrusted_host_rejected` | `Host: evil.com` → 400 |
| `test_trusted_host_accepted` | `Host: localhost` → 200 |
| `test_malformed_json_safe_422` | Malformed JSON → 422, no traceback/exception text |
| `test_unexpected_fields_do_not_crash` | Extra fields (`status`, `notes`, `role`) → 201, no injection |
| `test_unhandled_exception_returns_safe_500` | 500 → JSON `{"detail": ...}`, no internals, headers present |
| `test_validation_error_has_no_internal_details` | 422 body has no traceback |
| `test_session_cookie_flags` | `HttpOnly`, `SameSite=lax`, `Path=/`, no `Secure` in dev |
| `test_invalid_session_token_rejected` | Garbage cookie → 401 |
| `test_expired_session_rejected_and_cleaned` | Expired session → 401, row deleted |
| `test_logout_clears_session_cookie` | Logout sends an expiring `Set-Cookie` |

All tests run against the real PostgreSQL test database (session tests use real
session rows); the middleware tests exercise the real app. `test_health_db.py`
still passes (uses the `client` fixture).

Full suite: **226 passed** (211 prior + 15 new), no regressions.

## 12. Bugs discovered

1. **Logout never cleared the browser cookie (real bug).** `logout` called
   `clear_session_cookie(response)` on the injected `Response`, but then
   returned a **brand-new** `Response(status_code=204)`, discarding the cookie
   deletion. The server-side session row was deleted, but the browser kept the
   now-dead cookie until it expired. Found by writing the cookie-clearing
   assertion; the existing `test_logout_invalidates_session` only checked the
   server-side row and the `401` after logout, so it never caught this.
2. **Security headers missing on 500 responses.** The custom `Exception`
   handler's response had no security headers. Root cause: FastAPI routes
   `Exception`/`500` handlers to Starlette's **outermost** ServerErrorMiddleware,
   which sends its response via the raw ASGI `send` — bypassing the app's
   middleware stack (including the security-headers middleware). Reproduced with
   a minimal app before fixing.

## 13. Root causes

1. `logout` returned a new `Response` object instead of the one it mutated —
   a classic "mutate a dependency-injected response but return a different
   object" bug, previously masked because tests only verified server-side
   invalidation.
2. Starlette's `ServerErrorMiddleware` is intentionally the outermost wrapper
   and emits its 500 through the original `send`, so inner ASGI middleware
   cannot annotate it. FastAPI directs `@app.exception_handler(Exception)` to
   that middleware.

## 14. Fixes applied

1. **`logout`** now sets `response.status_code = 204` and returns the injected
   `response`, so the expired-cookie `Set-Cookie` header reaches the browser.
   Added `test_logout_clears_session_cookie` as a regression test.
2. **500 handling** — the `unhandled_exception_handler` now applies
   `SECURITY_HEADERS` to the `JSONResponse` it returns, guaranteeing the
   headers on 500s (documented in the handler). No behavioral regression: 500s
   remain safe JSON, exceptions are logged server-side, and TestClient's
   `raise_server_exceptions=True` still surfaces unexpected exceptions in tests.

## 15. Regression tests added

- `test_logout_clears_session_cookie` (cookie-clearing regression for the fix).
- `test_unhandled_exception_returns_safe_500` (safe-500 + headers + no leak).
- `test_session_cookie_flags`, `test_invalid_session_token_rejected`,
  `test_expired_session_rejected_and_cleaned` (session hardening).
- All 211 prior tests (auth, RBAC, CMS, leads, files, models, migration) still
  pass; conftest now enables CORS + trusted hosts without affecting any existing
  test (TestClient's `testserver` host is allowed).

## 16. Security checks

- **Headers**: nosniff / frame-deny / referrer-policy / permissions-policy on
  every response (verified on success, 404, and 500).
- **CORS**: configurable, disabled by default, credentials enabled when set;
  unknown origins get no ACAO header.
- **Trusted hosts**: configurable, disabled by default; untrusted Host → 400.
- **Error leakage**: malformed JSON/validation → 422 (no tracebacks); unexpected
  exceptions → JSON 500 with no internals; no SQLSTATE/connection strings/stack
  traces reach clients (re-verified).
- **SQL injection**: no raw SQL string interpolation in `app/` (scanned).
- **Path traversal**: storage keys are server-generated UUIDs; `_resolve` rejects
  absolute/`..`; folder regex-constrained (Phase 8, re-verified).
- **File upload**: MIME allowlist + size cap + UUID naming (Phase 8, re-verified).
- **Mass assignment**: schemas whitelist fields; models constructed explicitly
  (re-verified; extra fields ignored safely).
- **Secrets**: repo scan found no committed credentials/keys/tokens/URLs (only
  the `generate_session_token()` call in `auth.py` matched the token pattern —
  a runtime call, not a secret); `.env` and `/media/` are gitignored;
  `.env.example` has placeholders only.
- **PII**: no request-body or lead/media PII logging (logging is
  method/path/level only).

## 17. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv sync` | Clean (44 packages, unchanged) |
| `uv lock --check` | Resolved 44 packages, no drift |
| `uv run pytest` | **226 passed** (211 existing + 15 new) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 77 files already formatted |
| `uv run alembic check` | No new upgrade operations detected (no schema change) |
| `uv run alembic current` | `147c3d1fc707 (head)` |
| Secrets scan (tracked files) | Clean (no hardcoded credentials) |
| Raw-SQL-interpolation scan | Clean |

### Live endpoint verification (uvicorn on :8010 + curl)

Started the server with `CORS_ALLOWED_ORIGINS=http://localhost:3000` and
`TRUSTED_HOSTS=localhost,127.0.0.1`:

- Security headers present on `GET /health` (nosniff, DENY, referrer-policy).
- Allowed Origin → `access-control-allow-origin` + credentials; unknown Origin →
  no ACAO header.
- `Host: evil.com` → 400; `Host: localhost` → 200.
- Login `Set-Cookie` carries `HttpOnly`, `Max-Age`, `Path=/`, `SameSite=lax`.
- **Logout now sends an expiring `Set-Cookie`** (cookie actually cleared).
- Garbage session cookie → 401.
- Regression: public lead submission → 201, malformed JSON → 422, health/db and
  public CMS → 200.

Dev DB tables truncated and media removed after verification.

## 18. Known limitations

- **No rate limiting / anti-abuse controls** (login brute-force, registration
  abuse, lead spam). Not implemented because Redis would be required for a
  correct multi-worker limiter, and the roadmap permits introducing it only if
  justified. **Recommended before public launch** (see §22).
- **No CSP header** — a JSON API renders no HTML; revisit if HTML is ever
  served.
- **`COOKIE_SECURE` defaults to `false`** — must be `true` in production.
- **CORS/trusted hosts are disabled by default** — operators must configure
  them for production/Next.js integration.
- **Uploaded SVG served inline** can execute scripts when opened directly —
  production should serve media from a CDN/object storage with safe headers, or
  drop SVG from the allowlist.
- **Extra request fields are ignored, not rejected** — safe here (explicit
  construction), but stricter `extra="forbid"` schemas remain an option if a
  stricter API contract is desired.

## 19. Architecture / design decisions

- **Pure-ASGI security-headers middleware** instead of `BaseHTTPMiddleware` —
  avoids the extra hop and works for all response paths.
- **Config-driven CORS/trusted-hosts with empty defaults** — preserves existing
  dev/test behavior exactly (no host restrictions, no CORS) while providing the
  production knobs the frontend phase will need.
- **Safe 500 handler + explicit headers** — accepted the documented
  ServerErrorMiddleware bypass and worked around it in the handler rather than
  fighting the framework.
- **No Redis, no rate-limiting code** — consistent with "only introduce if
  justified"; documented as the top pre-launch gap instead.
- **No schema/dependency changes** — the phase was purely hardening.

## 20. Deferred work

- Rate limiting / throttling (Redis or gateway-level) for `/auth/*` and
  `/leads`.
- `extra="forbid"` on input schemas if a stricter API contract is wanted.
- CSP / HSTS at the edge (CDN/load balancer).
- Media served from a dedicated CDN/object-storage origin with safe headers
  (addresses SVG).
- MFA / password-reset flow (future auth phase).

## 21. Next phase

**Phase 10 — Testing & Quality Engineering** (comprehensive quality pass:
missing tests, correctness review, full-suite + lint + migration validation).

## 22. Security audit checklist and findings

| # | Area | Check | Result | Finding / action |
| --- | --- | --- | --- | --- |
| A1 | Auth | Session expiration enforced | ✅ | Expired → 401 + row deleted (tested) |
| A2 | Auth | Cookie flags | ✅ | HttpOnly, SameSite=lax, Path=/; Secure via `COOKIE_SECURE` |
| A3 | Auth | Logout invalidates session | ✅ | Server row deleted + cookie cleared (bug fixed) |
| A4 | Auth | Invalid session token | ✅ | 401 (tested) |
| A5 | Auth | Production cookie config | ⚠️ | `COOKIE_SECURE=true` + `__Host-` prefix recommended at deploy |
| B1 | Authz | All admin routes require staff | ✅ | `require_staff` on every `/admin/*` |
| B2 | Authz | No role bypass / escalation | ✅ | Register can't set role; role fields ignored |
| B3 | Authz | IDOR | ✅ | Staff-scoped object access; no per-object ownership surface |
| B4 | Authz | Unauthorized object access | ✅ | 401/403 verified live + tests |
| C1 | Validation | Max lengths | ✅ | Enforced on all input schemas |
| C2 | Validation | Malformed UUIDs | ✅ | 422 |
| C3 | Validation | Malformed JSON | ✅ | 422, safe body |
| C4 | Validation | Unexpected fields | ✅ | Ignored safely; explicit construction prevents injection |
| C5 | Validation | Dangerous values | ✅ | Slug/folder/email regexes; size caps |
| D1 | API | CORS | ✅ | Configurable; disabled by default; unknown origins rejected |
| D2 | API | Trusted hosts | ✅ | Configurable; untrusted Host → 400 |
| D3 | API | Security headers | ✅ | On success, 404, and 500 responses |
| D4 | API | Error leakage | ✅ | No stack traces/DB details/connection strings |
| D5 | API | SQL injection | ✅ | Parameterized queries only |
| D6 | API | Path traversal | ✅ | UUID keys; absolute/`..` rejected; folder regex |
| D7 | API | File upload security | ✅ | MIME allowlist, size cap, sanitized names |
| D8 | API | Mass assignment | ✅ | Whitelisted schemas + explicit construction |
| E1 | Abuse | Login brute-force | ⚠️ | **Not implemented** — rate limiting deferred; recommended pre-launch |
| E2 | Abuse | Registration abuse | ⚠️ | **Not implemented** — same |
| E3 | Abuse | Lead spam | ⚠️ | **Not implemented** — same |
| E4 | Abuse | Request throttling | ⚠️ | **Not implemented** (no Redis; not justified yet) |
| F1 | Secrets | API keys / passwords / URLs / tokens committed | ✅ | Clean scan |
| F2 | Secrets | `.env` ignored, `.env.example` placeholders | ✅ | Verified |
| F3 | Secrets | Config doesn't echo secrets | ✅ | No secret logging; config keeps defaults empty |

Legend: ✅ verified/fixed · ⚠️ finding (documented/deferred).