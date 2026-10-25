"""Docket's voice layer: the surface a person actually talks to.

Two Cartesia agents, each with its own number and its own instructions:

    CARTESIA_AGENT_ID          the payroll caller. Dials an employer, asks for one refund, records
                               what they promised. Started by the Caseworker on an approved case.
    CARTESIA_STUDENT_AGENT_ID  the student line. Two directions:
                                 out  Docket rings the student when a finding needs her, a document
                                      is ready to sign, or a group case is forming
                                 in   the student rings Docket and can ask anything; the question
                                      goes to the Athena research agent and the answer comes back
                                      on the same call

Both read their facts from Convex over the webhook tools in convex/http.ts, so the voice model never
holds a number of its own. What it may say is decided by agents/guard.py before the call starts.

Demo safety: every outbound call is redirected to DEMO_CALL_NUMBER (see calls.py). The researcher
still finds the real payroll and legal-aid numbers and stores them on the contact, so the call says
truthfully who it is for, but only the demo phone ever rings.
"""
