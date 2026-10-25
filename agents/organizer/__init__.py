"""Group cases: the students with the same problem, asking together.

One student asking payroll to fix one paycheck is easy to put off. Four students at the same employer
with the same finding is a payroll configuration error, and it is much harder to wave away — the fix
is the same for all of them, and so is the refund. That is the whole argument for this feature, and
it is also why every number in a group request is recomputed from the students who actually joined.

The rules this is built on, in order of how much they matter:

  1. Nobody is in a group request until they said yes. An invited student is not a member, their
     amount is not in the total, and their name is nowhere in the letter. "invited" and "joined" are
     different states for exactly this reason.

  2. A group never weakens an individual case. Joining adds a combined request; it does not pause,
     merge or close the student's own case, and declining costs her nothing.

  3. No student learns anything about another. The invitation says how many students are affected
     and names the employer. It never names another student, their amount, or their visa situation —
     agents/guard.py's "group" audience has no key that could carry one.

  4. The pattern is computed, not inferred. convex/groups.ts:candidates counts flags the rules engine
     wrote against the employer on the paystubs the rule hit on.
"""
