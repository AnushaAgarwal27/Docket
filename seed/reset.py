"""Wipe the demo state and re-seed Priya. Run before every rehearsal:
    .venv/bin/python -m seed.reset
Nessie reset joins this script once the Nessie seed exists.
"""

from agents.store import mutation

if __name__ == "__main__":
    profile_id = mutation("seed:resetDemo")
    print(f"Reset done. Priya's profile id: {profile_id}")
