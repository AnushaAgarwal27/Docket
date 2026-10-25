"""Upload a sample PDF to the dev SQLite deployment, read back its URL, and fetch it.

    .venv/bin/python -m scripts.upload_check [path/to.pdf]

Uses the first paystub PDF in seed/paystubs (synthetic) and the first paystub row in SQLite, so it
exercises the same helper the Ledger uses. Exits non-zero if the round trip fails.
"""
import sys
from pathlib import Path

import requests

from agents.convex_files import upload_and_attach
from agents.store import query


def main() -> int:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(Path("seed/paystubs").glob("*.pdf"))[0]
    profile = next(p for p in query("profiles:list") if not p.get("simulated"))
    stub = next(p for p in query("paystubs:listByProfile", {"profileId": profile["_id"]})
                if p["sourceFile"] == pdf.name)
    file_id = upload_and_attach(pdf, "paystub", agent="upload_check", paystubId=stub["_id"])
    if file_id is None:
        print("upload failed; see the activity feed")
        return 1
    flag = next(f for f in query("flags:listByProfile", {"profileId": profile["_id"]}) if f.get("paystubIds"))
    receipt = query("files:forFlag", {"flagId": flag["_id"]})
    url = next(f["url"] for f in receipt["paystubs"] if f["_id"] == file_id)
    import os
    url = os.environ.get("DOCKET_API_URL", "http://127.0.0.1:8000").rstrip("/") + url
    response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["DOCKET_API_TOKEN"]}, timeout=30)
    response.raise_for_status()
    body = response.content
    ok = body == pdf.read_bytes()
    print(f"uploaded {pdf.name} -> {file_id}\nurl: {url}\nread back {len(body)} bytes, {'identical' if ok else 'DIFFERENT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
