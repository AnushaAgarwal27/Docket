// POST /api/release-refund: the game's "post the refund to the test bank" button, on Vercel.
// Posts the payroll refund to the student's Capital One Nessie sandbox account; the Ledger agent
// then finds it on its own and closes the case. The Nessie key stays in Vercel's env, never in the page.
// Only posts when the case says payroll promised a refund, and only once per case.
const NESSIE = (process.env.NESSIE_BASE_URL || "https://api.nessieisreal.com").replace(/\/$/, "");
const PAYROLL = "University Dining Payroll";
const MEMO = "FICA refund";
const AWAITING_REFUND = ["awaiting_response", "written_request"];

async function caseFile() {
  const r = await fetch(`${process.env.CONVEX_URL.replace(/\/$/, "")}/api/query`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ path: "game:caseFile", args: {}, format: "json" }),
  });
  const j = await r.json();
  if (j.status !== "success") throw new Error(j.errorMessage || "Convex query failed");
  return j.value;
}

async function nessie(method, path, body) {
  const r = await fetch(`${NESSIE}${path}?key=${encodeURIComponent(process.env.NESSIE_API_KEY)}`, {
    method,
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`Nessie ${method} ${path}: ${r.status}`);
  return r.status === 204 ? null : r.json();
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).send("POST only");
  try {
    const file = await caseFile();
    const k = file && file.case;
    if (!k || !AWAITING_REFUND.includes(k.state)) {
      return res.status(409).send("No refund is due yet: payroll hasn't promised one on this case.");
    }
    // A reset wipes the sandbox and makes one new account; Nessie ids sort by creation time.
    const accounts = (await nessie("GET", "/accounts")) || [];
    const account = process.env.NESSIE_ACCOUNT_ID || accounts.map((a) => a._id).sort().at(-1);
    if (!account) return res.status(409).send("No Nessie account found; run the demo reset.");
    const deposits = (await nessie("GET", `/accounts/${account}/deposits`)) || [];
    if (deposits.some((d) => (d.description || "").includes(MEMO))) {
      return res.status(200).send("The refund deposit is already in the bank.");
    }
    const created = await nessie("POST", `/accounts/${account}/deposits`, {
      medium: "balance",
      transaction_date: new Date().toISOString().slice(0, 10),
      status: "completed",
      amount: k.amountCents / 100,
      description: `${PAYROLL} | ${MEMO}`,
    });
    return res.status(200).send(`Refund deposit ${created.objectCreated._id}`);
  } catch (e) {
    return res.status(500).send(String(e.message || e).slice(0, 300));
  }
};
