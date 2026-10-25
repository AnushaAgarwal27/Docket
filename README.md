# Docket

A caseworker for international students: organize paystubs, check potential payroll issues against stored official sources, challenge findings in a Hearing, request approval, contact payroll through Cartesia, and keep the case history.

Built at Cal Hacks 13.0. Synthetic demo only; not tax or immigration advice.

## Python + SQLite migration

Convex is no longer required. Python agents share `backend/store.py` through `agents/store.py`.
SQLite stores profiles, paystubs, transactions, sources, flags, hearings, cases, call outcomes and activity.
PDFs are stored beside the database. The React dashboard polls the authenticated Python API every 1.5 seconds.
All agent processes must run on the same machine, from the repo root, with the same `DOCKET_DB_PATH`.
Do not run different SQLite files on teammates' laptops and expect them to sync.
The prior Convex implementation remains available in Git history.

## Setup

Use Python 3.12 or 3.13 for uAgents.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
cp .env.example .env
```

Set these locally (never commit real secrets):

- `DOCKET_DB_PATH=data/docket.sqlite3`
- `DOCKET_API_URL=http://127.0.0.1:8000`
- `DOCKET_API_TOKEN`: generate with `openssl rand -hex 32`
- `CARTESIA_TOOL_TOKEN`: separate random secret, also configured in the two office tools
- Agent seeds and API keys for any live services being used.

## Initialize without deleting anything

```bash
python -m backend.initialize
```

This creates a **new synthetic** Priya profile, structured paystubs and transactions from `seed/demo_data.py`.
It refuses to change an existing student file. It does not pretend to have used Nessie or Claude extraction.
It does not seed fabricated official source text, manufacture a Hearing verdict or open an unverified case.

Then fetch sources (Apify preferred; plain-HTTP fallback available):

```bash
python -m seed.apify_sources
# or python -m seed.fetch_sources
```

Start the services in separate terminals, all at the repo root:

```bash
python -m backend.server
```

```bash
./scripts/run_agents.sh
```

```bash
npm run dashboard
```

Open the Vite URL. Enter `DOCKET_API_TOKEN` at the access screen. Use `?demo` only for the clearly
labelled offline rehearsal. Backend failure never silently switches live mode to demo data.
Use ASI:One `check my pay` to run the existing agent/rules/Hearing workflow and open an eligible case.
Missing official sources or unresolved Hearing objections can prevent a case; inspect Activity rather than bypassing the checks.

`python -m seed.reset` is still available, but **deletes SQLite demo records and can wipe Nessie sandbox data when its key is configured**.
It is not necessary for first initialization. Only use it when the team intends to reset the demonstration.

## Cartesia office caller

See [docs/CARTESIA.md](docs/CARTESIA.md). The same two tool paths now live on the Python server:

- `POST /cartesia/case-summary` — body `{ "case_id": "cases_..." }`
- `POST /cartesia/call-outcome` — case id, outcome, person, summary, optional date/reference

Both require `Authorization: Bearer <CARTESIA_TOOL_TOKEN>`.
Expose the service through a public **HTTPS** tunnel or host with persistent disk, and point the Cartesia tool URLs there.
Never leave the old `.convex.site` URLs configured. Do not expose an unauthenticated dashboard or raw database files.

Outbound calling remains in `agents/caseworker/cartesia.py`. Set `CARTESIA_API_KEY`, `CARTESIA_AGENT_ID`,
`CARTESIA_FROM_NUMBER_ID` and `PAYROLL_PHONE` (a consenting teammate for the demo).
With `CARTESIA_SIMULATE=1`, no real phone call is placed. Rehearsal tools call the local backend.
Approval and atomic claims prevent duplicate call starts; repeated outcome tool calls return the first outcome.
A failed or uncertain call start is not automatically retried, avoiding duplicate phone calls.
Calls that stall or are refused prepare a written request, not an automatically sent email.

## Student support line

`POST /cartesia/student-case-status` is a read-only endpoint for an **explicit synthetic demo profile**.
It returns case state, findings, call summaries, promised dates and follow-up dates. It does not approve anything.
Set `DOCKET_SYNTHETIC_SUPPORT=1`, `DOCKET_DEMO_PROFILE_ID` (printed by initialization), and a separate
`CARTESIA_SUPPORT_TOOL_TOKEN`. Configure that token in the student-support agent's tool.
Assign a phone number to that agent in Cartesia. Hindi listening/speaking must be configured and tested there.
Never use this single-profile demo endpoint for real students. Authenticated caller-to-profile binding is not implemented.

**Not implemented by this migration:** automatic student callbacks, legal-services-specific outbound briefings,
spoken approval, live conference interpreting, or an inbound explain-term tool. Existing payroll behavior is preserved.
No real Cartesia call or account configuration is performed by these code changes.

## Other integrations

The Fetch uAgents, Anthropic extraction/explanation, Nessie client, Apify collector and deterministic Hearing
remain in the repository. The Apify collector now saves official pages and activity to SQLite.
The dashboard's source-change popup uses the same activity feed and remembers dismissal locally.
This migration does not automatically schedule Apify runs; schedule the collector separately if desired.
Source wording, eligibility logic and form guidance still require independent review.

## Files and operations

- `backend/store.py`: transactions, stable query/mutation interface, case state machine.
- `backend/server.py`: token-protected API and Cartesia tools (stdlib HTTP server for a local demo).
- `backend/initialize.py`: non-destructive synthetic initialization.
- `dashboard/src/backend.tsx`: polling and authenticated PDF access.
- `dashboard/src/model.ts`: frontend response types independent of Convex.
- `agents/convex_files.py`: historical module name kept for imports; now writes local files only.

Host this demo on a trusted machine. The stdlib server is not a production authentication or hosting stack.
For production, add authenticated users, authorization, HTTPS deployment, input schemas, retention limits and durable job scheduling.
A Vercel static frontend alone cannot host the SQLite file; it needs a reverse proxy to the persistent Python service.

## Validation

```bash
python -m pytest tests -q
npx tsc -p dashboard/tsconfig.json
npm run dashboard:build
```

Agent-import tests need test seeds; do not use real keys. SQLite/HTTP tests use isolated temporary files
and a local server. They do not contact payroll, mutate a shared deployment or invoke live sponsor APIs.
