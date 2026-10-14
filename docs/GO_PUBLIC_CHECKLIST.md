# Go public checklist

Written 2026-10-15. These are steps for Ali to do by hand in the GitHub UI. Nothing here was done by Claude.

## State found on 2026-10-15

- `gh api repos/alyrraza/docdesk-healthcare-rag-evals` reported `"private": false`, so the repository is already public.
  The brief for this session said it was private. Check the repository settings and decide whether that is what you want.
- The container package visibility could not be read (the gh token has no `read:packages` scope). Check it in step 3.
- Secret scan on the full tree and on history (2026-10-15): no `gsk_` with 20 or more characters, no `AKIA` key, no `npg_`
  string and no real `sk-` key in any tracked file or in any commit. The only hit of the `sk-` pattern is the repository
  name itself, `docdesk-healthcare-rag-evals`, in `README.md` (the pattern matches the end of "docdesk"). It is not a secret.
- `.env`, `.cache/`, `evals/cache/` and `PROJECT_NOTES.md` are git-ignored and not tracked. `.env` on the laptop holds a real
  Groq key and the database url. It was never committed.

## What is in git history (finding F19)

Six local working notes were tracked in early commits and are still in history, even though they were untracked later
(commit 0c00880, "stop tracking internal working notes"):
`INSTALL.md`, `docs/COMMITS.md`, `docs/REFERENCES.md`, `docs/REMEMBER.md`, `docs/SKILLS.md`, `docs/WORKFLOW.md`.
They hold machine notes and workflow notes, no key was found in them. Anyone can read them in the old commits. Options:
leave them (they are harmless but personal), or rewrite history before anyone depends on the commit ids. A rewrite is a force
push and changes every commit id, so do it only on purpose, with a backup clone.

## Steps in the GitHub UI

1. Read the history once. Repository, Commits, open the first ten commits and the six files above. Decide leave or rewrite.
2. Repository visibility. Settings, General, Danger Zone, Change repository visibility. Only if it is not already public.
3. Package visibility. Your profile, Packages, `docdesk-healthcare-rag-evals`, Package settings, Danger Zone, Change
   visibility, Public. Also check "Manage Actions access" lists this repository with write access. A package made by a workflow
   from a public repository can still start as private, so look at it.
4. Test the pull without a login, from a machine where you are logged out of ghcr.io:
   `docker pull ghcr.io/alyrraza/docdesk-healthcare-rag-evals:latest`
5. Settings, Actions, General: workflow permissions can stay on "Read repository contents". The image-push job asks for
   `packages: write` by itself.
6. Settings, Secrets and variables: confirm no repository secret is stored that the workflows do not need. The workflows use none.
7. Settings, Code security: turn on secret scanning and push protection if they are available for this repository.
8. Add a repository description and topics (rag, fastapi, pgvector, evaluation, healthcare).
9. Read the README on github.com once as a stranger: the architecture image renders, the Mermaid diagram renders, links work.

## Keys

Any key that was ever pasted anywhere public (a screenshot, an issue, a chat, a gist, a commit) must be rotated, even if you
deleted it afterwards. Deleting does not remove copies. To rotate: create a new key in the provider console, put it in `.env`,
revoke the old one.

- Groq: console.groq.com, API Keys. There are two slots in use (`GROQ_API_KEY`, `GROQ_API_KEY_2`).
- Neon: the database password for the `docdesk` database role, if it was ever shown anywhere public.
- OpenRouter: only if a key was ever created (`OPENROUTER_API_KEY`).
- GitHub: the personal access token used by `gh`, if it was ever pasted anywhere.
