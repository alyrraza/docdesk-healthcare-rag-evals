---
paths:
  - "frontend/**/*.{ts,tsx,css}"
---

# Frontend rules

- Three pages only: login, chat with citations, dashboard. Nothing else without a PRD change.
- TypeScript strict mode. No `any`. API types come from one `api/types.ts` that mirrors
  the backend schemas in `docs/OUTPUTS.md`.
- One component per file, 200 lines or fewer. Data fetching lives in `api/` modules, never inside components.
- Every answer shows its citations with the source chunk text visible on click.
  An answer with no citation shows the abstain state, never a blank.
- The JWT is kept in memory plus an httpOnly cookie if the backend sets it; never in localStorage.
- Show loading, empty and error states for every request.
- Read `docs/modules/frontend.md` before editing.
