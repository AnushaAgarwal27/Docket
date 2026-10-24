# Gaps found in the build plan

1. **"Exactly two flags" vs three rules.** Priya is F-1 with no 8843 on record, so `needs_8843` fires
   too: three flags. Current choice: the seed records `filed8843Years: [2025]`, so the demo shows two.
2. **Hidden Nessie deposit.** Nessie has no "hidden" deposits. The "simulate 2 weeks" button should
   *create* the $440.64 deposit via the Nessie API when clicked.
3. **Schema fields the plan describes but the starter schema lacks** (added as optional in
   `convex/schema.ts`): paystub to deposit link, `cases.profileId`/deadline/draft, `calls.transcriptUrl`,
   `activity.inputIds/outputIds`, an 8843 filing record, a `by_nessie` index for dedupe.
4. **20-hour source.** The current eCFR text says "must not exceed 20 hours a week while school is in
   session" (numeral, not "twenty"). That exact wording is in rules.yaml and passes the quote checker.
5. **8843 deadline.** April 15 with US wages (filed with 1040-NR), June 15 with none.
6. **Name.** The plan says "Settle"; the repo is "Docket". Pick one before the Devpost draft.
