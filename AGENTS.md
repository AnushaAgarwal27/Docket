# Docket development

The runtime backend is Python + SQLite (`backend/`). Convex is no longer used.
All Python agents import `agents.store`; that adapter uses `backend.store` directly.
All processes must run from the repository root with the SAME DOCKET_DB_PATH.
HTTP tools are in backend/server.py; mutations must preserve transactional state transitions,
integer cents, approval gates, atomic call claims and idempotent outcome logging.
Dashboard data is polled through dashboard/src/backend.tsx; keep access tokens out of bundles.
Run `python -m pytest tests -q`, `npx tsc -p dashboard/tsconfig.json`, and
`npm run dashboard:build` before handing off. Never run reset scripts against shared data
or place calls without the user's authorization. Use temporary SQLite paths in tests.
