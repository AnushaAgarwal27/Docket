# Cartesia setup with the Python backend

1. Start `python -m backend.server` from the repository root with the same `.env` and SQLite path as the agents.
2. Configure random secrets `DOCKET_API_TOKEN`, `CARTESIA_TOOL_TOKEN`, and (for student support) `CARTESIA_SUPPORT_TOOL_TOKEN` locally.
3. Expose port 8000 through a public HTTPS tunnel. Keep the laptop, tunnel and Caseworker running.
4. In the Cartesia office agent, replace the old Convex URLs with:
   - `https://YOUR-PUBLIC-HOST/cartesia/case-summary`
   - `https://YOUR-PUBLIC-HOST/cartesia/call-outcome`
5. Both tools use Bearer authentication with `CARTESIA_TOOL_TOKEN`.
6. Summary request: `{ "case_id": "cases_..." }`. Use an actual SQLite case ID from the dashboard API;
   old Convex IDs and display labels do not exist in this database.
7. Outcome request: `case_id`, `result` (promised/stalled/refused/needs_student), `answered_by`, `summary`,
   optional `promised_by` (YYYY-MM-DD), optional `reference_number`.
8. Keep the existing AI disclosure and narrow payroll briefing. Always fetch the summary and log the outcome.
   Request a review, do not promise a refund or invent missing rules, dates, names or amounts.
9. Set `CARTESIA_AGENT_ID`, `CARTESIA_FROM_NUMBER_ID`, `CARTESIA_API_KEY`, and `PAYROLL_PHONE` on the machine running the Caseworker.
10. For a real test, unset `CARTESIA_SIMULATE` and approve a case addressed to a consenting teammate's number.
    Confirm the phone rings, the outcome tool succeeds, and the dashboard displays its summary, date and reference.

## Student support

Create a separate student-facing Managed Agent, with the `get_student_case_status` webhook:
`POST https://YOUR-PUBLIC-HOST/cartesia/student-case-status`, empty JSON body, Bearer `CARTESIA_SUPPORT_TOOL_TOKEN`.
Explicitly enable the synthetic demo with `DOCKET_SYNTHETIC_SUPPORT=1` and set `DOCKET_DEMO_PROFILE_ID` to the
initialized synthetic student's ID. Never bind a real caller by name, masked phone or an arbitrary first profile.
The agent must say it is an AI and the line uses fictional student records. Read only the latest tool result.
A follow-up date is not a scheduled call; a refund promise is not a deposit. Failure means say the case is unavailable.
Do not approve outreach from this read-only tool. Configure and test Hindi in both recognition and voice settings
before claiming bilingual support. Assign an inbound number in Cartesia to make the agent reachable.

Automatic callbacks to students and legal-services outreach need separate implementation and are not enabled here.

## Failures

- 401: wrong/missing tool token.
- 400 Record not found: incorrect SQLite case ID, empty database, or wrong shared database path.
- 400 Source quote cannot be verified: refresh and review official sources; do not bypass the gate.
- Case approved but no call: check Caseworker process, call errors, simulation setting, credentials and destination.
- File access: PDFs require the dashboard token, fetched by the frontend and opened as local browser blobs.

Rehearsal sets `CARTESIA_SIMULATE=1` and uses `DOCKET_API_URL` for the same HTTP tools.
Only use synthetic records and consenting teammate numbers. Never send keys in screenshots or commit `.env`.
