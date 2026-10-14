# Module: frontend

Created 2026-10-13. Criteria: AC-FE-01 to 03. Small on purpose: the backend and the evals are the project.

## Built so far: the single page UI (2026-10-15)
A plain HTML, CSS and JavaScript page is served by the API itself from `src/docdesk/web/static/`.
No npm, no build step, no outside requests (a test greps for URLs and for `innerHTML`). It covers a sign in and register panel,
a question box with three examples, an outcome badge (Answered, Abstained, Refused), numbered citations that open the source text,
a collapsible retrieval panel fed by `POST /retrieve`, and a plain message when generation is unavailable (503). The React plan
above (upload panel, dashboard) is still open in `docs/PLAN.md`.

## Stack
React, TypeScript (strict), Vite. Plain CSS modules. One small chart library chosen at task T146.

## Pages (three only)
1. Login and register (AC-FE-01).
2. Chat: upload a document and see its status, ask a question, see the answer with the disclaimer.
   Citations are listed under the answer. Clicking one shows the source chunk text and document title (AC-FE-02).
   An abstained answer shows the reason in plain words, never a blank.
3. Dashboard (admin sees all traces, a user sees own): p50 and p95 per stage, cost per query,
   failure labels, active prompt versions and the activate button for admins (AC-FE-03).

## Structure
```
frontend/src/
  api/        client.ts, types.ts (mirrors OUTPUTS.md), auth.ts, documents.ts, query.ts, traces.ts
  components/ one component per file: AnswerCard, CitationList, UploadPanel, StageLatencyChart, ...
  pages/      LoginPage.tsx, ChatPage.tsx, DashboardPage.tsx
  state/      auth store
```
Data fetching lives in `api/`, never inside components.

## Rules
- No `any`. Types mirror the backend schemas.
- JWT kept in memory (and an httpOnly cookie if the backend sets it), never localStorage.
- Every request has loading, empty and error states. Errors show the trace id so a bug report can be traced.
- Components under 200 lines.

## Tests
Component tests for AnswerCard (citations, abstain state), CitationList (reveal), and the auth flow with a mocked API.
