"""Write the Cartesia dashboard fields to files, so building the agents is select-all and paste.

    .venv/bin/python -m scripts.write_paste_files

Produces cartesia-paste/, one file per dashboard field. The prompts are long and the exact wording
is what keeps the voice model from inventing a tax answer, so retyping them is the step most likely
to go wrong. Open the file, select all, paste.

The directory is gitignored: the tool files carry the webhook bearer token.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from agents.caseworker.rehearsal import site_url
from scripts.make_cartesia_agents import AGENTS

load_dotenv()

OUT = Path(__file__).resolve().parent.parent / "cartesia-paste"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    base = site_url()
    token = os.environ.get("CARTESIA_TOOL_TOKEN", "")

    written = []
    for _env_key, name, voice, intro, prompt, tools in AGENTS:
        opening = OUT / f"{name}--1-opening-message.txt"
        opening.write_text(intro + "\n")
        system = OUT / f"{name}--2-system-prompt.txt"
        system.write_text(prompt + "\n")

        lines = [
            f"Webhook tools for {name}   (suggested voice: {voice})",
            "",
            "Every one of these: method POST, auth type Bearer, execution immediate, timeout 10s.",
            f"Bearer token: {token}",
            "",
            "-" * 78,
        ]
        for tool_name, path, pre, desc, params in tools:
            lines += [
                "",
                f"TOOL NAME        {tool_name}",
                f"URL              {base}{path}",
                f"DESCRIPTION      {desc}",
                f"BODY FIELDS      {params}",
                f"PRE-TOOL SPEECH  {pre}",
                "",
                "-" * 78,
            ]
        tools_file = OUT / f"{name}--3-tools.txt"
        tools_file.write_text("\n".join(lines) + "\n")
        written += [opening, system, tools_file]

    print(f"\nWrote {len(written)} files to {OUT}/\n")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name}")
    print("\nOpen each one, select all, paste into the matching dashboard field.")
    print(f"These contain your webhook token, so {OUT.name}/ is gitignored.\n")


if __name__ == "__main__":
    main()
