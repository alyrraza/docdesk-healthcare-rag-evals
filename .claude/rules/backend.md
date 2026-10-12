---
paths:
  - "src/docdesk/api/**/*.py"
  - "src/docdesk/auth/**/*.py"
  - "src/docdesk/db/**/*.py"
  - "src/docdesk/core/**/*.py"
---

# Backend rules

- Routers are thin: parse input, call one service function, shape the response.
  No business logic and no SQL inside a router.
- Every route has an explicit auth dependency. The only public routes are the
  ones in `PUBLIC_ROUTES` in `api/public.py`; a test fails if another route is public.
- All errors leave the API in the standard envelope from `core/errors.py`:
  `{"error": {"code", "message", "trace_id"}}`. Never return a raw exception text.
- Passwords: hashed with a slow salted hash from `auth/passwords.py`. JWT secrets
  come from settings, never from code. Token lifetime is short.
- Database access goes through `db/` repositories. Use parameterized queries only.
  Sessions are opened per request and always closed (use the dependency, not globals).
- Migrations are Alembic only. Never edit a migration that was already committed;
  add a new one.
- Read `docs/modules/backend.md` for interfaces and acceptance criteria.
