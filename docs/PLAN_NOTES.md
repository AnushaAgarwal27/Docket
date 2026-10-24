# Gaps found in the build plan

1. **"Exactly two flags" vs three rules.** Priya is F-1 with no 8843 on record, so `needs_8843` fires
   too: three flags. Fix: seed `filed8843Years: [2025]` for Priya, or change the done-condition to three.
2. **Hidden Nessie deposit.** Nessie has no "hidden" deposits. The "simulate 2 weeks" button should
   *create* the $440.64 deposit via the Nessie API when clicked.
3. **Schema fields the plan describes but the starter schema lacks** (added as optional in
   `convex/schema.ts`): paystub to deposit link, `cases.profileId`/deadline/draft, `calls.transcriptUrl`,
   `activity.inputIds/outputIds`, an 8843 filing record, a `by_nessie` index for dedupe.
4. **20-hour source.** 8 CFR 214.2(f)(9)(i) has a quotable sentence ("may not exceed twenty hours a
   week while school is in session"). Verify against the fetched text before using it.
5. **8843 deadline.** April 15 with US wages (filed with 1040-NR), June 15 with none.
6. **Name.** The plan says "Settle"; the repo is "Docket". Pick one before the Devpost draft.
