import React from 'react';
// The live quote check fetches IRS Publication 519 through a same-origin proxy:
// vite.config.js proxies it in dev, api/p519.js proxies it on Vercel. If it fails, the app
// falls back to the copy verified Oct 24, 2026 and says so on screen.
const IRS_FETCH_URL = import.meta.env.VITE_IRS_PROXY || '/api/p519';

const FONT_HREF = "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Figtree:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap";
const DISPLAY = "'Fraunces', Georgia, serif";
const SANS = "'Figtree', -apple-system, 'Segoe UI', Helvetica, sans-serif";
const MONO = "'IBM Plex Mono', ui-monospace, Menlo, monospace";
const K = {
  paper: '#F3ECDF', wall: '#EADFCB', floor: '#DCC9A8', card: '#FBF7EF', ink: '#2A2520',
  muted: 'rgba(42,37,32,0.74)', faint: 'rgba(42,37,32,0.52)', rule: 'rgba(42,37,32,0.14)',
  green: '#2F5D50', greenSoft: 'rgba(47,93,80,0.12)', red: '#B5503E', redSoft: 'rgba(181,80,62,0.12)',
  kraft: '#C9A877', kraftDark: '#A88553', kraftDeep: '#7A5A33',
  shadow: '0 1px 0 rgba(60,40,20,0.06), 0 16px 30px -18px rgba(60,40,20,0.5)',
};
const HONEST = 'Prototype · scripted · no real call placed';
const CONFIRM = "Confirm with your school's international office.";
const BANNER = "Made-up quote caught: Docket's own AI drafted a quote that isn't in the IRS text. Code checked it and threw it out before anyone saw it.";
const DRAFT = 'F-1 students never pay Social Security or Medicare tax.';
const P519 = {
  quote: 'Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien.',
  title: 'IRS Publication 519 (2025), U.S. Tax Guide for Aliens',
  section: 'Chapter 8 · Nonresident Alien Students',
  url: 'https://www.irs.gov/publications/p519#:~:text=Social%20security%20and%20Medicare%20taxes%20are%20not%20withheld%20from%20pay%20for%20the%20work%20unless%20the%20student%20is%20considered%20a%20resident%20alien',
};
const OBJ = ['Year count boundary', 'Employer is a contractor', 'Student exception applies', 'Medicare recovery uncertain'];
const ROUND_META = [
  { id: 'hearing', title: 'The Hearing', place: 'Courtroom' },
  { id: 'call', title: 'The Call', place: 'Switchboard' },
  { id: 'money', title: 'The Money', place: 'Vault' },
];
const NOW_YEAR = new Date().getFullYear();
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
// Every case runs through the same rules in code: count calendar years from the arrival date, exempt for years 1 to 5.
function makeCase(d) {
  const parts = String(d.arrival).split('-').map(Number), y = parts[0], m = parts[1], day = parts[2];
  const yearNo = NOW_YEAR - y + 1, exempt = yearNo >= 1 && yearNo <= 5;
  const ss = d.ss || 0, med = d.med || 0, total = ss + med;
  const P = d.custom ? { S: 'They', s: 'they', her: 'their', is: 'are' } : { S: 'She', s: 'she', her: 'her', is: 'is' };
  const c = Object.assign({}, d, P, {
    arrivalYear: y, yearNo, exempt, ss, med, total,
    arrivalLong: MONTHS[m - 1] + ' ' + day + ', ' + y, arrivalShort: MON3[m - 1] + ' ' + day + ', ' + y, monthYear: MONTHS[m - 1] + ' ' + y,
    verdict: exempt ? 'UPHELD' : 'DEFEATED', recovered: exempt ? total : 0,
    hoursLine: d.custom ? 'Weekly work hours' : 'Her weekly work hours',
  });
  c.claimLine = money(ss) + ' Social Security + ' + money(med) + ' Medicare = ' + money(total);
  c.facts = d.facts || [
    c.visa + ' · arrived ' + c.arrivalShort + ' · ' + NOW_YEAR + ' is year ' + yearNo + (exempt ? ' of 5' : ''),
    (c.employer || 'Employer') + (c.stubs ? ' · ' + c.stubs + ' paystubs' : ''),
    total ? c.claimLine + ' withheld' : 'Social Security and Medicare withheld',
  ];
  return c;
}
const CASES = {
  priya: makeCase({ id: 'priya', name: 'Priya Sharma', first: 'Priya', visa: 'F-1', arrival: '2024-08-15', employer: 'University Dining Services', stubs: 8, ss: 35712, med: 8352 }),
  nadia: makeCase({ id: 'nadia', name: 'Nadia Petrova', first: 'Nadia', visa: 'F-1', arrival: '2019-01-07', facts: ['F-1 · arrived Jan 7, 2019', NOW_YEAR + ' is year ' + (NOW_YEAR - 2019 + 1) + ' in the US', 'Social Security and Medicare withheld'] }),
};
// Deep links: text fragments jump to (and highlight) the exact sentence on the official page.
function frag(base, start, end) { const e = s => encodeURIComponent(s).replace(/-/g, '%2D'); return base + '#:~:text=' + e(start) + (end ? ',' + e(end) : ''); }
const P519_URL = 'https://www.irs.gov/publications/p519';
const SRC = {
  student: { label: 'IRS Pub 519 · Nonresident Alien Students', url: frag(P519_URL, 'Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien') },
  fiveYears: { label: 'IRS Pub 519 · the 5-calendar-year rule for students', url: frag(P519_URL, 'You will not be an exempt individual as a student in 2025', 'more than 5 calendar years') },
  studentTip: { label: 'IRS Pub 519 · the student exception (Tip)', url: frag(P519_URL, 'Any student who is enrolled and regularly attending classes at a school may be exempt') },
  refund: { label: 'IRS Pub 519 · Refund of Taxes Withheld in Error', url: frag(P519_URL, 'If social security or Medicare tax was withheld in error from pay that is not subject to these taxes') },
  b19: { label: '26 U.S.C. § 3121(b)(19) · the law itself (Cornell LII)', url: 'https://www.law.cornell.edu/uscode/text/26/3121#b_19' },
  b10: { label: '26 U.S.C. § 3121(b)(10) · the law itself (Cornell LII)', url: 'https://www.law.cornell.edu/uscode/text/26/3121#b_10' },
};

function money(c) { c = Math.max(0, Math.round(c)); return '$' + Math.floor(c / 100).toLocaleString('en-US') + '.' + String(c % 100).padStart(2, '0'); }

// ---------- folded-paper cast ----------
function Shadow({ cx, cy, rx }) { return <ellipse cx={cx} cy={cy} rx={rx} ry="3.5" fill="rgba(60,40,20,0.14)" />; }
function Crane() {
  return (
    <svg viewBox="0 0 120 100" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="62" cy="91" rx="34" />
      <polygon points="60,56 34,6 52,58" fill="#8BBFAD" />
      <polygon points="60,56 34,6 44,40" fill="#A9D2C3" />
      <polygon points="12,42 42,62 36,68" fill="#3B7362" />
      <polygon points="36,68 60,54 60,80" fill="#5A9A85" />
      <polygon points="60,54 86,66 60,80" fill="#3F7A67" />
      <polygon points="60,57 80,8 68,60" fill="#4F8C78" />
      <polygon points="60,57 80,8 72,40" fill="#6BA893" />
      <polygon points="82,66 100,20 88,64" fill="#2F5D50" />
      <polygon points="96,20 106,22 118,30 100,28" fill="#25493F" />
      <circle cx="104" cy="24.5" r="1.4" fill="#F3ECDF" />
    </svg>
  );
}
function Fox() {
  return (
    <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="52" cy="95" rx="36" />
      <polygon points="72,92 97,58 86,86" fill="#B5542A" />
      <polygon points="97,58 90,70 99,70" fill="#F2E3CC" />
      <polygon points="30,56 50,56 50,94 18,94" fill="#D9773F" />
      <polygon points="50,56 70,56 82,94 50,94" fill="#C2602C" />
      <polygon points="40,62 60,62 50,90" fill="#F2E3CC" />
      <polygon points="16,6 36,30 14,32" fill="#C2602C" />
      <polygon points="20,13 31,28 18,29" fill="#5A3A28" />
      <polygon points="84,6 86,32 64,30" fill="#B5542A" />
      <polygon points="80,13 82,29 69,28" fill="#5A3A28" />
      <polygon points="12,30 50,30 50,72" fill="#E8935C" />
      <polygon points="50,30 88,30 50,72" fill="#D9773F" />
      <polygon points="28,46 50,72 50,56" fill="#F5E8D3" />
      <polygon points="72,46 50,56 50,72" fill="#EAD9BE" />
      <polygon points="46,67 54,67 50,73" fill="#2A2520" />
      <polygon points="30,40 41,42 32,45" fill="#2A2520" />
      <polygon points="70,40 59,42 68,45" fill="#2A2520" />
    </svg>
  );
}
function Owl() {
  return (
    <svg viewBox="0 0 100 110" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="50" cy="106" rx="30" />
      <polygon points="20,24 27,4 38,27" fill="#6C5136" />
      <polygon points="80,24 73,4 62,27" fill="#5E472F" />
      <polygon points="20,24 50,30 50,102 20,72" fill="#8A6A4A" />
      <polygon points="80,24 80,72 50,102 50,30" fill="#765A3E" />
      <polygon points="22,30 50,34 50,64 26,58" fill="#E3D2B4" />
      <polygon points="78,30 74,58 50,64 50,34" fill="#D6C29F" />
      <polygon points="34,68 50,64 66,68 50,100" fill="#A7835C" />
      <polygon points="43,66 57,66 50,78" fill="#F7F1E6" />
      <circle cx="37" cy="46" r="10" fill="#FBF7EF" />
      <circle cx="63" cy="46" r="10" fill="#FBF7EF" />
      <text x="37" y="51.6" textAnchor="middle" fontFamily={MONO} fontSize="15" fontWeight="600" fill="#2A2520">{'{'}</text>
      <text x="63" y="51.6" textAnchor="middle" fontFamily={MONO} fontSize="15" fontWeight="600" fill="#2A2520">{'}'}</text>
      <polygon points="46,55 54,55 50,62" fill="#D99A3E" />
      <polygon points="38,102 42,108 46,102" fill="#D99A3E" />
      <polygon points="54,102 58,108 62,102" fill="#D99A3E" />
    </svg>
  );
}
function Turtle() {
  const c = '60,44';
  const rim = [[16, 58], [24, 38], [40, 22], [60, 15], [80, 22], [96, 38], [104, 58]];
  const cols = ['#9AA868', '#7F8E4F', '#B0BC7E', '#8D9B5C', '#A3B070', '#6F7F43'];
  return (
    <svg viewBox="0 0 120 80" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="60" cy="73" rx="46" />
      <polygon points="26,56 16,70 36,62" fill="#6E7F45" />
      <polygon points="84,58 98,70 92,56" fill="#6E7F45" />
      <polygon points="96,48 114,42 116,54 100,58" fill="#8C9C5A" />
      <circle cx="108" cy="47" r="1.6" fill="#2A2520" />
      {rim.slice(0, -1).map((p, i) => <polygon key={i} points={p.join(',') + ' ' + rim[i + 1].join(',') + ' ' + c} fill={cols[i]} />)}
      <polygon points={'104,58 16,58 ' + c} fill="#7A8A4A" />
      <polygon points="14,58 106,58 100,64 20,64" fill="#5E6B38" />
      <rect x="54" y="40" width="12" height="9" rx="1.5" fill="#FBF7EF" />
      <path d="M56.5 40v-2.6a3.5 3.5 0 0 1 7 0V40" fill="none" stroke="#FBF7EF" strokeWidth="1.8" />
      <circle cx="60" cy="44.5" r="1.3" fill="#5E6B38" />
    </svg>
  );
}
function FilingBox() {
  return (
    <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="54" cy="94" rx="36" />
      <polygon points="48,26 70,18 74,28 52,34" fill="#FFFDF8" />
      <polygon points="18,30 58,20 86,30 46,40" fill="#E0C597" />
      <polygon points="18,30 46,40 46,92 18,82" fill="#B08F5E" />
      <polygon points="46,40 86,30 86,82 46,92" fill="#C9A877" />
      <line x1="46" y1="66" x2="86" y2="56" stroke="#A88553" strokeWidth="1.4" />
      <circle cx="57" cy="47" r="2.3" fill="#2A2520" />
      <circle cx="73" cy="43" r="2.3" fill="#2A2520" />
      <polygon points="59,57 73,53.5 73,56.5 59,60" fill="#7A5A33" />
      <polygon points="52,74 64,71 64,78 52,81" fill="#FBF7EF" />
      <polygon points="68,74 80,71 80,74 68,77" fill="#7A5A33" />
    </svg>
  );
}
function Frog() {
  return (
    <svg viewBox="0 0 100 90" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="50" cy="87" rx="38" />
      <polygon points="12,74 30,50 36,82" fill="#5E8C3E" />
      <polygon points="88,74 70,50 64,82" fill="#4F7A33" />
      <polygon points="30,38 50,32 50,84 24,74" fill="#7FA65A" />
      <polygon points="70,38 76,74 50,84 50,32" fill="#6D9449" />
      <polygon points="38,58 50,54 62,58 50,82" fill="#C8D99A" />
      <polygon points="24,32 36,16 48,34" fill="#8DB566" />
      <polygon points="76,32 64,16 52,34" fill="#7FA65A" />
      <circle cx="36" cy="27" r="6" fill="#FBF7EF" />
      <circle cx="64" cy="27" r="6" fill="#FBF7EF" />
      <g className="dc-pupils"><circle cx="37" cy="27" r="3" fill="#2A2520" /><circle cx="65" cy="27" r="3" fill="#2A2520" /></g>
      <path d="M40 44 Q50 50 60 44" stroke="#2A2520" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <polygon points="34,84 26,88 42,88" fill="#5E8C3E" />
      <polygon points="66,84 58,88 74,88" fill="#4F7A33" />
    </svg>
  );
}
function CodeTile() {
  return (
    <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block' }} aria-hidden>
      <polygon points="14,20 86,14 90,82 10,86" fill="#2A2520" />
      <polygon points="14,20 86,14 50,48" fill="#3D352D" />
      <text x="50" y="62" textAnchor="middle" fontFamily={MONO} fontSize="30" fontWeight="600" fill="#F3ECDF">{'{ }'}</text>
    </svg>
  );
}
function Gavel() {
  return (
    <svg viewBox="0 0 70 50" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <polygon points="30,22 66,40 62,46 26,28" fill="#A06B42" />
      <polygon points="6,8 30,4 34,26 10,30" fill="#7A4E2E" />
      <polygon points="6,8 30,4 31,10 7,14" fill="#94643E" />
      <polygon points="16,6 22,5 26,28 20,29" fill="#C9A877" />
    </svg>
  );
}
function oct(r, cx, cy, rot) { const a = []; for (let i = 0; i < 8; i++) { const t = (i * 45 + (rot || 22.5)) * Math.PI / 180; a.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]); } return a; }
function VaultDoor({ spinning, open }) {
  const o = oct(48, 50, 50), inr = oct(36, 50, 50);
  const shades = ['#B9A47F', '#A8926C', '#C7B38E', '#9C875F', '#B4A07A', '#A38D66', '#C0AC86', '#98835C'];
  return (
    <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      {o.map((p, i) => { const q = o[(i + 1) % 8], a = inr[i], b = inr[(i + 1) % 8]; return <polygon key={i} points={[p, q, b, a].map(x => x.join(',')).join(' ')} fill={shades[i]} />; })}
      <polygon points={inr.map(x => x.join(',')).join(' ')} fill="#D8C7A4" />
      <g className={spinning ? 'dc-spin' : ''} style={{ transformOrigin: '50px 50px', transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 1.2s cubic-bezier(.3,.7,.2,1)' }}>
        {[0, 60, 120].map(d => <rect key={d} x="47.5" y="20" width="5" height="60" rx="1" fill="#7A5A33" transform={'rotate(' + d + ' 50 50)'} />)}
        <circle cx="50" cy="50" r="9" fill="#5E472F" />
        <circle cx="50" cy="50" r="4" fill="#D99A3E" />
      </g>
    </svg>
  );
}

function Student() {
  return (
    <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block', overflow: 'visible' }} aria-hidden>
      <Shadow cx="50" cy="94" rx="30" />
      <polygon points="50,40 76,92 24,92" fill="#C9A877" />
      <polygon points="50,40 76,92 50,92" fill="#B08F5E" />
      <polygon points="38,62 50,40 62,62 50,70" fill="#2F5D50" />
      <polygon points="50,10 66,24 50,40 34,24" fill="#E8C9A6" />
      <polygon points="50,10 66,24 50,24" fill="#D9B48C" />
      <polygon points="34,24 50,8 66,24 58,16 42,16" fill="#2A2520" />
      <rect x="56" y="58" width="14" height="22" rx="2" fill="#FBF7EF" stroke="#2A2520" strokeWidth="1.6" />
      <path d="m59.5 69 2.5 2.5 4.5-5" fill="none" stroke="#2F5D50" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const CAST = {
  crane: { name: 'Crane', role: 'Advocate', note: 'Docket, argues for the student', Art: Crane },
  fox: { name: 'Fox', role: 'Auditor', note: 'argues for the employer', Art: Fox },
  owl: { name: 'Owl', role: 'Judge', note: 'rules decided in code', Art: Owl },
  turtle: { name: 'Turtle', role: 'Guardian', note: 'protects student privacy', Art: Turtle },
  box: { name: 'Filing box', role: 'Payroll clerk', note: 'the employer’s payroll office', Art: FilingBox },
  frog: { name: 'Frog', role: 'Ledger', note: 'tracks the bank', Art: Frog },
  code: { name: 'Quote checker', role: 'Code, not AI', note: 'checks quotes word for word', Art: CodeTile },
  priya: { name: 'Priya', role: 'Student · the human', note: 'approves anything Docket does for her', Art: Student },
};

// ---------- the script (only the figures from the brief) ----------
function opt(id, title, detail, correct, feedback, extra) { return Object.assign({ id, title, detail, correct: !!correct, feedback: feedback || '' }, extra || {}); }

function buildRounds(c, irs) {
  const n = c.yearNo, ay = c.arrivalYear, Y = NOW_YEAR, emp = c.employer || 'the employer';
  const live = irs && irs.status === 'live';
  const checkWhere = live ? 'the live IRS Publication 519 page (fetched ' + irs.time + ')' : 'the IRS Publication 519 text (copy verified Oct 24, 2026)';
  const opening = [
    { who: 'owl', text: 'Court is in session. Case: ' + c.name + ', ' + c.visa + '. Claim: Social Security and Medicare were withheld in error.' },
    { who: 'crane', text: 'Filing the claim. My first draft cites the IRS like this:', card: { kind: 'draft' } },
    { who: 'code', fx: 'shred', text: 'Searched ' + checkWhere + ' for that sentence. Not found. Quote rejected and shredded.', card: { kind: 'draft', shred: true }, banner: BANNER },
    { who: 'crane', fx: 'verify', text: c.exempt && c.total
        ? 'Refiled with the exact clause, checked word for word. Claim: ' + c.claimLine + (c.stubs ? ', across ' + c.stubs + ' paystubs.' : '.')
        : 'Refiled with the exact clause, checked word for word.', card: { kind: 'quote' } },
  ];
  if (!c.exempt) {
    return [{ meta: ROUND_META[0], beats: opening.concat([
      { who: 'fox', text: 'I argue for the employer. My first objection should settle this.' },
      { who: 'fox', obj: { n: 1, s: 'raised' }, text: 'Objection 1, year count boundary. ' + c.S + ' arrived ' + c.arrivalLong + '. ' + ay + ' is year 1, so ' + Y + ' is year ' + n + '. The exemption covers 5 calendar years.' },
      { who: 'crane', choice: {
        prompt: 'Pick the evidence card that answers objection 1.',
        watchText: 'I checked the count myself. It’s right, and I won’t argue against the facts.',
        options: [
          opt('fake', 'Say ' + c.s + ' arrived in ' + (Y - 4), 'That would put ' + (c.custom ? 'them' : 'her') + ' inside the 5 years', false, 'Rejected. Docket never changes the facts, even to win.'),
          opt('count', 'Calendar year count', 'Arrived ' + c.arrivalShort + ' · ' + Y + ' is year ' + n, true, '', { lines: ['Arrived ' + c.arrivalShort, ay + ' is year 1', Y + ' is year ' + n + ', past the 5-year limit'],
            plain: c.first + ' arrived in ' + c.monthYear + '. The IRS counts calendar years, not months, so ' + Y + ' is year ' + n + '. Students are usually exempt only for their first 5 calendar years. After that they usually count as US residents for tax, and residents do pay Social Security and Medicare. So the withholding is likely correct, and Docket says so. One narrow exception: a student past 5 years can still be exempt if they show they don’t intend to live in the US permanently and have kept to their visa rules. Code can’t judge that from a date, so Docket flags it for the international office instead of claiming it.',
            src: [SRC.fiveYears, SRC.student] }),
          opt('clause', 'The IRS clause', 'Publication 519 on student pay', false, 'That clause only helps while ' + c.s + ' ' + c.is + ' a nonresident alien. After 5 calendar years ' + c.s + ' likely ' + (c.custom ? 'aren’t' : 'isn’t') + ', so it doesn’t apply.'),
        ] } },
      { who: 'owl', obj: { n: 1, s: 'sustained' }, text: 'Counted in code: ' + Y + ' is year ' + n + ', past the 5-year limit. Objection sustained.' },
      { who: 'owl', fx: 'stamp', stamp: 'DEFEATED', objRest: true, text: 'Claim DEFEATED. After 5 calendar years ' + c.s + ' likely ' + (c.custom ? 'count' : 'counts') + ' as a resident alien for tax, so the withholding is likely correct. Objections 2 to 4 are not needed.' },
    ]) }];
  }
  const hearing = opening.concat([
    { who: 'fox', text: 'I argue for the employer. I have four objections.' },
    { who: 'fox', obj: { n: 1, s: 'raised' }, text: 'Objection 1, year count boundary. ' + c.S + ' arrived in ' + c.monthYear + '. Count that partial year as a full one and ' + c.s + ' could already be near ' + c.her + ' 5-year limit.' },
    { who: 'crane', choice: {
      prompt: 'Pick the evidence card that answers objection 1.',
      watchText: 'Answering with the calendar year count.',
      options: [
        opt('days', 'Count days, not years', 'Only part of ' + ay + ' was spent in the US', false, 'Wrong rule. The exemption counts calendar years, and any part of a year counts as a full one.'),
        opt('id', 'Her student ID', 'Proves she is enrolled', false, 'Enrollment doesn’t answer a year-count question.'),
        opt('count', 'Calendar year count', 'Arrived ' + c.arrivalShort + ' · ' + Y + ' is year ' + n + ' of 5', true, '', { lines: ['Arrived ' + c.arrivalShort, ay + ' is year 1: any part of a year counts', Y + ' is year ' + n + ' of 5'],
          plain: c.first + ' arrived in ' + c.monthYear + '. The IRS counts calendar years, not months, so ' + ay + ' is year 1 even though ' + c.s + ' only spent part of it here. ' + Y + ' is year ' + n + '. Students get 5 calendar years, so ' + c.s + ' ' + c.is + ' still inside the window. The fox’s worry is real, it just doesn’t apply yet.',
          src: [SRC.fiveYears] }),
      ] } },
    { who: 'owl', obj: { n: 1, s: 'overruled' }, text: 'Counted in code: ' + ay + ' is year 1, so ' + Y + ' is year ' + n + ' of 5. ' + c.S + ' ' + c.is + ' inside the limit. Overruled.' },
    { who: 'fox', obj: { n: 2, s: 'raised' }, text: 'Objection 2, the employer may be a contractor, not the university. Then the school’s rules don’t apply.' },
    { who: 'crane', choice: {
      prompt: 'Pick the evidence card that answers objection 2.',
      watchText: 'The exemption follows her status, not who signs her paycheck.',
      options: [
        opt('status', 'Basis: her ' + c.visa + ' status', 'IRC 3121(b)(19) follows her status, not her employer', true, '', { lines: ['Nonresident alien in ' + c.visa + ' status: IRC 3121(b)(19)', 'Covers work her ' + c.visa + ' status allows, whoever the employer is'].concat(c.employer ? ['Employer on her paystubs: ' + c.employer] : []),
          plain: 'The fox is hinting that a company, not the university, might be paying ' + c.first + '. It doesn’t matter. The tax law (section 3121(b)(19)) excludes work done by a nonresident student on an ' + c.visa + ' visa doing the work that visa allows. The exemption comes from ' + c.her + ' visa status, not from who signs the paycheck.',
          src: [SRC.b19, SRC.student] }),
        opt('studentx', 'The student exception', 'IRC 3121(b)(10), for school employees', false, 'That exception needs the school itself as employer. If it’s a contractor, it fails. Use the stronger ground.'),
        opt('wage', 'Her hourly wage', 'What she earns per hour', false, 'Pay rate doesn’t decide the exemption.'),
      ] } },
    { who: 'owl', obj: { n: 2, s: 'overruled' }, text: 'The exemption follows her status. Who signs the paycheck doesn’t change it. Overruled.' },
    { who: 'fox', obj: { n: 3, s: 'raised' }, text: 'Objection 3, the student exception applies instead. That needs proof she is enrolled at least half time, and you don’t have it.' },
    { who: 'crane', choice: {
      prompt: 'Pick the evidence card that answers objection 3.',
      watchText: 'The claim doesn’t rest on the student exception at all.',
      options: [
        opt('drop', 'Drop the claim', 'We can’t prove half-time enrollment', false, 'Too fast. The claim doesn’t depend on enrollment.'),
        opt('grounds', 'Two separate grounds', 'The claim rests on 3121(b)(19), not the student exception', true, '', { lines: ['The claim rests on IRC 3121(b)(19): nonresident status', 'The student exception, IRC 3121(b)(10), is a separate extra ground', 'The claim doesn’t need it'],
          plain: 'There are two different reasons a student might not owe these taxes. Reason 1 (section 3121(b)(19)): ' + c.first + ' is a nonresident on an ' + c.visa + ' visa. Reason 2 (section 3121(b)(10), the “student exception”): any enrolled student working for their own school. The fox attacks reason 2, which needs proof of enrollment. Docket’s claim only uses reason 1, so knocking down reason 2 changes nothing.',
          src: [SRC.b19, SRC.b10, SRC.studentTip] }),
        opt('schedule', 'Her class schedule', 'Shows she attends classes', false, 'Not needed. The claim stands on her nonresident status.'),
      ] } },
    { who: 'owl', obj: { n: 3, s: 'overruled' }, text: 'The claim stands on its own ground. Overruled.' },
    { who: 'fox', obj: { n: 4, s: 'raised' }, text: 'Objection 4. Maybe Social Security comes back, but Medicare recovery is uncertain.' },
    { who: 'crane', choice: {
      prompt: 'Pick the evidence card that answers objection 4.',
      watchText: 'The official clause names both taxes.',
      options: [
        opt('ssonly', 'Ask for Social Security only', 'Settle for ' + money(c.ss), false, 'That leaves ' + money(c.med) + ' behind. The clause covers Medicare too.'),
        opt('blog', 'A tax blog post', 'Says Medicare is refundable', false, 'Not an official source. Docket only cites official text, checked word for word.'),
        opt('p519', 'IRS Publication 519', 'The clause, word for word', true, '', { quote: true,
          plain: 'This is the IRS’s own sentence, and it names both taxes: Social Security and Medicare. So both amounts come back, ' + money(c.ss) + ' and ' + money(c.med) + ', not just one.' }),
      ] } },
    { who: 'owl', obj: { n: 4, s: 'overruled' }, text: 'The clause names both taxes. Overruled.' },
    { who: 'owl', fx: 'stamp', stamp: 'UPHELD', text: 'All four objections overruled. Rules checked in code: ' + c.visa + ', year ' + n + ' of 5, likely exempt. Claim UPHELD: ' + money(c.total) + ' likely owed.' },
  ]);
  const call = [
    { who: 'priya', card: { kind: 'callreq' }, choice: { approval: true, approvalTitle: 'Call ' + emp + ' payroll about ' + money(c.total),
      prompt: 'Docket asks ' + c.first + ' first: “May I call ' + emp + ' payroll about the ' + money(c.total) + '? I’ll say I’m an AI calling with your permission.”',
      watchText: c.first + ' approved the call. Docket does nothing for her until she says yes.',
      options: [
        opt('approve', 'Approve the call', 'Docket may call payroll for me', true, ''),
        opt('no', 'Not yet', 'Don’t contact my employer', false, 'Okay. Docket won’t contact payroll without ' + c.first + '’s yes. In this demo, approve to continue.'),
      ] } },
    { who: 'crane', fx: 'ring', text: 'Dialing ' + emp + ' payroll.' },
    { who: 'crane', text: 'Hi, this is Docket, an AI calling with ' + c.name + '’s permission. This call may be recorded. I’m calling about Social Security and Medicare withheld from ' + c.her + ' pay.' },
    { who: 'box', fx: 'stall', text: 'Hmm. I’d have to check with our tax team. We can’t change anything over the phone.' },
    { who: 'crane', choice: {
      prompt: 'Payroll is stalling. What does Docket do?',
      watchText: 'No problem. I’ll put it in writing so you have everything in one place.',
      options: [
        opt('pretend', 'Say “This is ' + c.first + '”', 'Pretend to be the student so payroll moves faster', false, 'Blocked. Docket says it’s an AI and never pretends to be the student.'),
        opt('write', 'Send a written request', 'Put the claim in writing so payroll can act on it', true, '', { lines: ['Payroll gets the claim, the numbers and the IRS clause in writing'],
          plain: 'Payroll can’t fix this on a phone call. The IRS says to ask the employer for the refund first, so a written request gives payroll the numbers and the rule in one place, and gives ' + c.first + ' a record. If payroll still says no, the next step is IRS Form 843.',
          src: [SRC.refund] }),
        opt('quit', 'Drop the case', 'Payroll didn’t say yes on the phone', false, 'A stall isn’t a no. Put it in writing first.'),
      ] } },
    { who: 'crane', text: 'Drafting the written request.', card: { kind: 'letter' } },
    { who: 'turtle', fx: 'block', text: 'Blocked the line “' + c.hoursLine + '”. ' + c.first + '’s work hours aren’t needed for a tax refund request. Private details stay out of anything sent to ' + c.her + ' employer.', card: { kind: 'letter' } },
    { who: 'priya', card: { kind: 'review' }, choice: { approval: true, approvalTitle: 'Send this exact letter to payroll',
      prompt: c.first + ' reviews the exact letter before anything is sent. The removed line is shown struck out.',
      watchText: c.first + ' read the final letter and approved sending it.',
      options: [
        opt('send', 'Approve and send', 'Send this exact letter', true, ''),
        opt('hold', 'Hold', 'Don’t send yet', false, 'Held. Nothing is sent without ' + c.first + '’s approval. In this demo, approve to continue.'),
      ] } },
    { who: 'crane', fx: 'send', text: 'Written request sent to payroll, with the work-hours line removed. I’ll follow up until the money is back.' },
    { who: 'box', text: 'Got it. We’ll review the request.' },
  ];
  const moneyRound = [
    { who: 'frog', fx: 'watch', text: 'I’m the Ledger. I watch ' + c.first + '’s bank account and match each deposit to an open case. Waiting for a deposit from ' + emp + '.' },
    { who: 'frog', fx: 'deposit', text: 'A deposit just landed: ' + money(c.total) + ' from ' + emp + '.' },
    { who: 'frog', fx: 'match', choice: {
      prompt: 'Should the Ledger match this deposit to ' + c.first + '’s case?',
      watchText: 'The case expects ' + money(c.total) + '. The deposit is ' + money(c.total) + '. Exact match.',
      options: [
        opt('any', 'Close on any deposit', 'Money arrived, so the case is done', false, 'Docket only closes a case on an exact match.'),
        opt('wait', 'Ignore it and keep waiting', 'Maybe more is coming', false, 'It matches the claim to the cent. No reason to wait.'),
        opt('match', 'Match it to the case', money(c.total) + ' = ' + money(c.ss) + ' + ' + money(c.med), true, '', { lines: ['Case expects: ' + money(c.ss) + ' + ' + money(c.med) + ' = ' + money(c.total), 'Deposit: ' + money(c.total) + ' from ' + emp, 'Exact match'],
          plain: 'A refund should equal exactly what was withheld: ' + money(c.ss) + ' + ' + money(c.med) + ' = ' + money(c.total) + '. A deposit for exactly that amount, from the same employer, is how Docket knows this is the refund and not a normal paycheck.' }),
      ] } },
    { who: 'frog', fx: 'close', stamp: 'CASE CLOSED', text: 'Matched to the case, to the cent. Case closed.' },
    { who: 'crane', text: c.first + '’s money is back. Docket is done with this case.' },
  ];
  return [
    { meta: ROUND_META[0], beats: hearing },
    { meta: ROUND_META[1], beats: call },
    { meta: ROUND_META[2], beats: moneyRound },
  ];
}

function optCard(o, c) { return o.quote ? { kind: 'quote', plain: o.plain } : { kind: 'evidence', title: o.title, lines: o.lines || [o.detail], plain: o.plain, src: o.src }; }

function useCountUp(target, ms) {
  const [v, setV] = React.useState(0);
  const cur = React.useRef(0);
  React.useEffect(() => {
    const dur = ms || 1000;
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const from = cur.current;
    if (reduce || from === target) { cur.current = target; setV(target); return; }
    const t0 = performance.now(); let raf = 0, done = false;
    const tick = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      const val = Math.round(from + (target - from) * e);
      cur.current = val; setV(val);
      if (k < 1) raf = requestAnimationFrame(tick); else done = true;
    };
    raf = requestAnimationFrame(tick);
    const fb = setTimeout(() => { if (!done) { cancelAnimationFrame(raf); cur.current = target; setV(target); } }, dur + 300);
    return () => { cancelAnimationFrame(raf); clearTimeout(fb); };
  }, [target]);
  return v;
}


// ================= 3D WORLD (three.js r169 from jsDelivr) =================
const THREE_URL = 'https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js';
let __threeP = null;
function loadThree() { if (!__threeP) { __threeP = import('three').catch(e => { __threeP = null; throw e; }); } return __threeP; }
const EASE = {
  lin: t => t,
  inOut: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  out: t => 1 - Math.pow(1 - t, 3),
  in: t => t * t * t,
  back: t => { const c1 = 1.5, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
};
const CHAR_ORDER = ['crane', 'fox', 'owl', 'turtle', 'box', 'frog'];
const SLOTS = {
  hearing: { crane: [-1.75, 0, 1.0, -0.35], fox: [1.8, 0, 1.0, Math.PI + 0.35], owl: [0, 1.01, -1.42, -Math.PI / 2] },
  call: { crane: [-1.95, 0, 0.9, -0.3], box: [2.0, 0, 0.7, Math.PI + 0.3], turtle: [0, 0, 1.75, -Math.PI / 2] },
  money: { frog: [-1.55, 0, 1.25, -0.6], crane: [-2.35, 0, -0.4, -0.5] },
};

function createWorld(THREE, mount, hooks) {
  const V3 = THREE.Vector3;
  const PW = 6, PD = 7.6;
  const coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  const lowFX = coarse || Math.min(window.innerWidth, window.innerHeight) < 560;
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DS = reduce ? 0.3 : 1;
  const O = new V3(PW / 2, 0.1, 0);

  // ---------- renderer / scene ----------
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lowFX ? 1.5 : 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.style.display = 'block';
  renderer.domElement.style.width = '100%';
  renderer.domElement.style.height = '100%';
  renderer.domElement.style.touchAction = 'pan-y';
  mount.appendChild(renderer.domElement);
  const maxAniso = renderer.capabilities.getMaxAnisotropy();
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#5A4330');
  scene.fog = new THREE.Fog('#5A4330', 24, 56);
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 140);

  const hemi = new THREE.HemisphereLight('#FFF4E2', '#6E5236', 1.35);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight('#FFF1DC', 2.3);
  sun.position.set(-7, 15, 9);
  sun.castShadow = true;
  sun.shadow.mapSize.set(lowFX ? 1024 : 2048, lowFX ? 1024 : 2048);
  const sc = sun.shadow.camera; sc.left = -11; sc.right = 11; sc.top = 11; sc.bottom = -11; sc.near = 1; sc.far = 45;
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02; sun.shadow.radius = 4;
  sun.target.position.set(1.5, 0, 0); scene.add(sun.target); scene.add(sun);
  const fill = new THREE.DirectionalLight('#FFE7C8', 0.45); fill.position.set(8, 6, -6); scene.add(fill);

  // ---------- tweens ----------
  const tweens = [];
  function tw(o) { const t = Object.assign({ delay: 0, dur: 0.6, ease: EASE.inOut }, o); t.delay *= DS; t.dur = Math.max(0.001, t.dur * DS); t.t0 = performance.now(); t.started = false; t.dead = false; tweens.push(t); return t; }
  function tickTweens(now) {
    for (let i = 0; i < tweens.length; i++) {
      const t = tweens[i]; if (t.dead) continue;
      const el = (now - t.t0) / 1000 - t.delay; if (el < 0) continue;
      if (!t.started) { t.started = true; t.start && t.start(); }
      const k = Math.min(1, el / t.dur);
      t.update && t.update(t.ease(k), k);
      if (k >= 1) { t.dead = true; t.done && t.done(); }
    }
    for (let i = tweens.length - 1; i >= 0; i--) if (tweens[i].dead) tweens.splice(i, 1);
  }
  function finishAll() {
    let guard = 0;
    while (tweens.some(t => !t.dead) && guard++ < 60) {
      const cur = tweens.slice();
      for (const t of cur) { if (t.dead) continue; if (!t.started) { t.started = true; t.start && t.start(); } t.update && t.update(t.ease(1), 1); t.dead = true; t.done && t.done(); }
    }
    tweens.length = 0;
  }
  function moveTo(obj, to, o) {
    o = o || {}; let from, fr, fs;
    return tw(Object.assign({}, o, {
      start() { from = obj.position.clone(); fr = obj.rotation.clone(); fs = obj.scale.x; o.onStart && o.onStart(); },
      update(e, k) {
        obj.position.lerpVectors(from, to, e);
        if (o.arc) obj.position.y += Math.sin(Math.PI * k) * o.arc;
        if (o.rot) { obj.rotation.x = fr.x + (o.rot[0] - fr.x) * e; obj.rotation.y = fr.y + (o.rot[1] - fr.y) * e + (o.spins || 0) * Math.PI * 2 * e; obj.rotation.z = fr.z + (o.rot[2] - fr.z) * e; }
        if (o.scale != null) obj.scale.setScalar(fs + (o.scale - fs) * e);
        o.onUpdate && o.onUpdate(e, k);
      },
      done() { o.onDone && o.onDone(); },
    }));
  }
  function damp(a, b, k, dt) { return a + (b - a) * (1 - Math.exp(-k * dt)); }
  function dampAngle(a, b, k, dt) { let d = b - a; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2; return a + d * (1 - Math.exp(-k * dt)); }
  let shakeAmt = 0;
  function shake(a) { if (!reduce) shakeAmt = Math.max(shakeAmt, a); }

  // ---------- materials / geometry helpers ----------
  const matCache = {};
  function M(color, opts) { const key = color + (opts ? JSON.stringify(Object.keys(opts).map(k => k + (opts[k] && opts[k].isTexture ? opts[k].uuid : opts[k]))) : ''); if (!matCache[key]) matCache[key] = new THREE.MeshLambertMaterial(Object.assign({ color, flatShading: true }, opts || {})); return matCache[key]; }
  const creaseMat = new THREE.LineBasicMaterial({ color: '#3A2A1A', transparent: true, opacity: 0.2 });
  function mesh(geo, color, opts, noCrease) {
    const m = new THREE.Mesh(geo, color && color.isMaterial ? color : M(color, opts));
    m.castShadow = true; m.receiveShadow = true;
    if (!lowFX && !noCrease) m.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo, 24), creaseMat));
    return m;
  }
  function part(geo, color, pos, rot, scl, opts) { const m = mesh(geo, color, opts); if (pos) m.position.set(pos[0], pos[1], pos[2]); if (rot) m.rotation.set(rot[0], rot[1], rot[2]); if (scl) m.scale.set(scl[0], scl[1], scl[2]); return m; }
  function tris(arr) { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(arr.flat(), 3)); g.computeVertexNormals(); return g; }

  // ---------- canvas textures ----------
  const FD = (px, w) => (w || 600) + ' ' + px + "px Fraunces, Georgia, serif";
  const FSn = (px, w) => (w || 500) + ' ' + px + "px Figtree, Helvetica, Arial, sans-serif";
  const FMo = (px, w) => (w || 600) + ' ' + px + "px 'IBM Plex Mono', Menlo, monospace";
  function canvasTex(w, h, draw) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const ctx = c.getContext('2d'); draw(ctx, w, h);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = maxAniso; t.userData.canvas = c; t.userData.ctx = ctx; return t;
  }
  function redraw(t, draw) { const c = t.userData.canvas, ctx = t.userData.ctx; ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, c.width, c.height); draw(ctx, c.width, c.height); t.needsUpdate = true; }
  function wrapLines(ctx, text, maxW) { const words = String(text).split(' '); const out = []; let cur = ''; for (const w of words) { const s = cur ? cur + ' ' + w : w; if (ctx.measureText(s).width > maxW && cur) { out.push(cur); cur = w; } else cur = s; } if (cur) out.push(cur); return out; }
  function fibers(c, w, h, n, dark) { c.save(); for (let i = 0; i < n; i++) { c.strokeStyle = dark ? 'rgba(60,40,20,0.07)' : 'rgba(120,90,50,0.05)'; c.lineWidth = 1 + Math.random(); const x = Math.random() * w, y = Math.random() * h, a = Math.random() * Math.PI, l = 4 + Math.random() * 14; c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); c.stroke(); } c.restore(); }
  function rrect(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
  function spaced(c, text, x, y, sp) { let cx = x; for (const ch of text) { c.fillText(ch, cx, y); cx += c.measureText(ch).width + sp; } }

  const woodTex = canvasTex(1024, 1024, (c, w, h) => {
    c.fillStyle = '#8A6A45'; c.fillRect(0, 0, w, h);
    for (let p = 0; p < 8; p++) { c.fillStyle = p % 2 ? 'rgba(255,240,215,0.035)' : 'rgba(40,25,10,0.04)'; c.fillRect(0, p * 128, w, 128); c.fillStyle = 'rgba(40,25,10,0.22)'; c.fillRect(0, p * 128, w, 2); }
    for (let i = 0; i < 260; i++) { c.strokeStyle = Math.random() < 0.5 ? 'rgba(70,48,25,0.13)' : 'rgba(190,150,100,0.10)'; c.lineWidth = 1 + Math.random() * 2; const y0 = Math.random() * h, amp = 2 + Math.random() * 6, f = 0.004 + Math.random() * 0.01; c.beginPath(); for (let x = 0; x <= w; x += 16) { const y = y0 + Math.sin(x * f + i) * amp; x ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke(); }
  });
  woodTex.wrapS = woodTex.wrapT = THREE.RepeatWrapping; woodTex.repeat.set(7, 7);
  const blobTex = canvasTex(128, 128, (c, w) => { const g = c.createRadialGradient(64, 64, 4, 64, 64, 62); g.addColorStop(0, 'rgba(30,18,8,0.55)'); g.addColorStop(1, 'rgba(30,18,8,0)'); c.fillStyle = g; c.fillRect(0, 0, w, w); });
  const dotTex = canvasTex(64, 64, (c) => { const g = c.createRadialGradient(32, 32, 1, 32, 32, 30); g.addColorStop(0, 'rgba(255,248,230,0.95)'); g.addColorStop(1, 'rgba(255,248,230,0)'); c.fillStyle = g; c.fillRect(0, 0, 64, 64); });

  function pageFrontDraw(cs, i) {
    return (c, w, h) => {
      c.fillStyle = '#F4EDE0'; c.fillRect(0, 0, w, h); fibers(c, w, h, 1400);
      c.strokeStyle = 'rgba(47,93,80,0.09)'; c.lineWidth = 2; for (let y = 150; y < h; y += 56) { c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
      c.strokeStyle = 'rgba(181,80,62,0.2)'; c.beginPath(); c.moveTo(96, 0); c.lineTo(96, h); c.stroke();
      c.fillStyle = '#2A2520'; c.font = FMo(30); c.fillText('ROUND ' + (i + 1) + ' · ' + ROUND_META[i].title.toUpperCase(), 124, 74);
      c.textAlign = 'right'; c.fillStyle = 'rgba(42,37,32,0.6)'; c.fillText(cs.name.toUpperCase(), w - 46, 74); c.textAlign = 'left';
    };
  }
  function pageBackDraw(i, summary, verdict) {
    return (c, w, h) => {
      c.save(); c.translate(w, 0); c.scale(-1, 1);
      c.fillStyle = '#EFE6D6'; c.fillRect(0, 0, w, h); fibers(c, w, h, 1200);
      c.fillStyle = 'rgba(42,37,32,0.7)'; c.font = FMo(30); c.fillText('ROUND ' + (i + 1) + ' · ' + ROUND_META[i].title.toUpperCase(), 90, 100);
      if (summary) {
        c.fillStyle = '#2A2520'; c.font = FD(66, 500); const ls = wrapLines(c, summary, w - 180); ls.forEach((l, k) => c.fillText(l, 90, 230 + k * 80));
        c.font = FMo(28); c.fillStyle = 'rgba(42,37,32,0.55)'; c.fillText('ON THE RECORD', 90, 260 + ls.length * 80);
        if (verdict) { const col = verdict === 'DEFEATED' ? '#B5503E' : '#2F5D50'; c.save(); c.translate(w / 2, h - 300); c.rotate(-0.12); c.strokeStyle = col; c.lineWidth = 10; rrect(c, -260, -70, 520, 140, 14); c.stroke(); c.fillStyle = col; c.font = FMo(84); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(verdict, 0, 4); c.restore(); }
      }
      c.restore();
    };
  }
  function coverDraw(cs, extra) {
    return (c, w, h) => {
      c.fillStyle = '#C9A877'; c.fillRect(0, 0, w, h); fibers(c, w, h, 2200, true);
      c.fillStyle = '#FBF7EF'; rrect(c, 110, 160, w - 220, 560, 18); c.fill(); c.strokeStyle = 'rgba(42,37,32,0.25)'; c.lineWidth = 3; c.stroke();
      c.fillStyle = '#2F5D50'; c.fillRect(110, 160, 26, 560);
      c.fillStyle = 'rgba(42,37,32,0.65)'; c.font = FMo(34); spaced(c, 'CASE FILE', 170, 250, 6);
      c.fillStyle = '#2A2520'; c.font = FD(104); c.fillText(cs.name, 170, 380);
      c.font = FSn(38); c.fillStyle = 'rgba(42,37,32,0.78)';
      let y = 460; cs.facts.forEach(f => { wrapLines(c, f, w - 330).forEach(l => { c.fillText(l, 170, y); y += 52; }); });
      if (extra) { c.fillStyle = '#FBF7EF'; rrect(c, 110, 770, w - 220, 140, 18); c.fill(); c.fillStyle = '#B5503E'; c.font = FSn(50, 700); c.fillText(extra, 160, 858); }
    };
  }
  const cardCache = {};
  function cardTex(kind, label, title, body) {
    const key = [kind, label, title, body].join('|'); if (cardCache[key]) return cardCache[key];
    const band = { objection: '#C8693F', evidence: '#2F5D50', draft: '#B5503E', quote: '#2A2520', wrong: '#8A7F72', approval: '#2A2520' }[kind] || '#2A2520';
    const t = canvasTex(512, 680, (c, w, h) => {
      c.fillStyle = '#FBF7EF'; c.fillRect(0, 0, w, h); fibers(c, w, h, 300);
      c.fillStyle = band; c.fillRect(0, 0, w, 96);
      c.fillStyle = '#FBF7EF'; c.font = FMo(25); c.fillText(label, 30, 60);
      c.fillStyle = '#2A2520'; c.font = FD(kind === 'quote' || kind === 'draft' ? 34 : 46, kind === 'quote' || kind === 'draft' ? 500 : 600);
      let y = 165; const lh = kind === 'quote' || kind === 'draft' ? 46 : 56;
      wrapLines(c, title, w - 60).forEach(l => { c.fillText(l, 30, y); y += lh; });
      if (body) { c.font = FSn(28); c.fillStyle = 'rgba(42,37,32,0.7)'; y += 14; wrapLines(c, body, w - 60).forEach(l => { c.fillText(l, 30, y); y += 38; }); }
      c.strokeStyle = 'rgba(42,37,32,0.25)'; c.lineWidth = 4; c.strokeRect(2, 2, w - 4, h - 4);
    });
    cardCache[key] = t; return t;
  }
  const stampCache = {};
  function stampTex(text, color) {
    const key = text + color; if (stampCache[key]) return stampCache[key];
    const t = canvasTex(1024, 340, (c, w, h) => {
      c.strokeStyle = color; c.lineWidth = 18; rrect(c, 22, 22, w - 44, h - 44, 26); c.stroke();
      c.lineWidth = 5; rrect(c, 52, 52, w - 104, h - 104, 16); c.stroke();
      c.fillStyle = color; const size = Math.min(150, (w - 170) / (text.length * 0.62)); c.font = FMo(size, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(text, w / 2, h / 2 + 6);
      c.globalCompositeOperation = 'destination-out'; for (let i = 0; i < 2200; i++) { c.fillStyle = 'rgba(0,0,0,' + (0.3 + Math.random() * 0.5) + ')'; c.beginPath(); c.arc(Math.random() * w, Math.random() * h, 0.6 + Math.random() * 2.4, 0, Math.PI * 2); c.fill(); }
    });
    stampCache[key] = t; return t;
  }
  function letterLines(cs) { return [
    ['mono', 'WRITTEN REQUEST', 72],
    ['sans', 'To: ' + (cs.employer || 'the employer') + ' payroll', 150],
    ['sans', 'Re: Social Security and Medicare withheld in error', 200],
    ['rule', '', 236],
    ['sans', 'Withheld' + (cs.stubs ? ' across ' + cs.stubs + ' paystubs' : '') + ': ' + cs.claimLine, 290],
    ['sans', 'Basis: IRS Publication 519, quoted word for word', 405],
    ['sans', 'Sent by Docket, an AI agent, with ' + cs.first + '’s permission', 590],
  ]; }
  function letterDraw(cs) {
    return (c, w, h) => {
      c.fillStyle = '#FFFDF8'; c.fillRect(0, 0, w, h); fibers(c, w, h, 300);
      letterLines(cs).forEach(([k, t, y]) => {
        if (k === 'rule') { c.fillStyle = 'rgba(42,37,32,0.18)'; c.fillRect(60, y, w - 120, 3); return; }
        c.fillStyle = '#2A2520'; c.font = k === 'mono' ? FMo(30) : FSn(34);
        wrapLines(c, t, w - 120).forEach((l, i) => c.fillText(l, 60, y + i * 46));
      });
      c.strokeStyle = 'rgba(42,37,32,0.2)'; c.lineWidth = 4; c.strokeRect(2, 2, w - 4, h - 4);
    };
  }
  const letterTex = canvasTex(1024, 720, letterDraw(CASES.priya));
  function hoursDraw(cs) { return (c, w, h) => { c.fillStyle = '#FFFDF8'; c.fillRect(0, 0, w, h); c.fillStyle = '#2A2520'; c.font = FSn(34, 600); c.fillText(cs.hoursLine, 60, 54); }; }
  const hoursTex = canvasTex(1024, 82, hoursDraw(CASES.priya));
  function bankFrontDraw(cs) {
    return (c, w, h) => {
      c.fillStyle = '#2F5D50'; c.fillRect(0, 0, w, h); fibers(c, w, h, 600, true);
      c.fillStyle = 'rgba(243,236,223,0.8)'; c.font = FMo(40); spaced(c, 'LEDGER WATCH', 70, 100, 6);
      c.fillStyle = '#D9B867'; rrect(c, 70, 190, 150, 112, 14); c.fill();
      c.fillStyle = '#F3ECDF'; c.font = FSn(60, 700); c.fillText(cs.first + '’s account', 70, 470);
      c.font = FSn(42); c.fillStyle = 'rgba(243,236,223,0.85)'; c.fillText('Simulated feed · watching for deposits', 70, 545);
    };
  }
  const bankFrontTex = canvasTex(1024, 640, bankFrontDraw(CASES.priya));
  function bankBackDraw(cents, matched, emp) {
    return (c, w, h) => {
      c.fillStyle = '#FBF7EF'; c.fillRect(0, 0, w, h); fibers(c, w, h, 400);
      c.fillStyle = 'rgba(42,37,32,0.55)'; c.font = FMo(40); spaced(c, 'DEPOSIT', 70, 100, 6);
      c.fillStyle = '#2F5D50'; c.font = FD(160, 500); c.fillText(money(cents), 64, 300);
      c.fillStyle = 'rgba(42,37,32,0.75)'; c.font = FSn(46); c.fillText(emp || 'University Dining Services', 70, 400);
      c.font = FSn(46, 700); c.fillStyle = matched ? '#2F5D50' : 'rgba(42,37,32,0.45)'; c.fillText(matched ? '✓ Exact match to case' : 'Checking the case…', 70, 510);
      c.strokeStyle = 'rgba(42,37,32,0.2)'; c.lineWidth = 6; c.strokeRect(3, 3, w - 6, h - 6);
    };
  }
  const bankBackTex = canvasTex(1024, 640, bankBackDraw(0, false));
  function eyeTex(ch) { return canvasTex(128, 128, (c) => { c.fillStyle = '#FBF7EF'; c.beginPath(); c.arc(64, 64, 60, 0, Math.PI * 2); c.fill(); c.fillStyle = '#2A2520'; c.font = FMo(86, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(ch, 64, 68); }); }
  const eyeL = eyeTex('{'), eyeR = eyeTex('}');
  const boardLabelTex = canvasTex(1024, 150, (c, w, h) => { c.fillStyle = '#7A5A33'; c.font = FMo(84, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('SWITCHBOARD', w / 2, h / 2 + 4); });
  const emblemTex = canvasTex(256, 256, (c, w) => { c.fillStyle = '#E0CFAF'; c.beginPath(); for (let i = 0; i < 8; i++) { const a = (i * 45 + 22.5) * Math.PI / 180; c.lineTo(128 + 124 * Math.cos(a), 128 + 124 * Math.sin(a)); } c.fill(); c.fillStyle = '#7A5A33'; c.font = FMo(96, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('{ }', 128, 132); });

  // ---------- desk ----------
  const desk = new THREE.Mesh(new THREE.PlaneGeometry(90, 90), new THREE.MeshLambertMaterial({ map: woodTex }));
  desk.rotation.x = -Math.PI / 2; desk.receiveShadow = true; scene.add(desk);

  // ---------- origami cast (forward = +x) ----------
  function blob(r) { const b = new THREE.Mesh(new THREE.PlaneGeometry(r, r), new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, opacity: 0.55 })); b.rotation.x = -Math.PI / 2; b.position.y = 0.012; return b; }
  function buildCrane() {
    const root = new THREE.Group(), body = new THREE.Group(); root.add(body);
    body.add(part(new THREE.OctahedronGeometry(0.5, 0), '#4F8C78', [0, 0.5, 0], null, [1.25, 0.62, 0.6]));
    body.add(part(new THREE.ConeGeometry(0.075, 1.0, 4), '#2F5D50', [0.6, 0.98, 0], [0, 0, -0.42]));
    const head = new THREE.Group(); head.position.set(0.8, 1.43, 0); body.add(head);
    head.add(part(new THREE.OctahedronGeometry(0.1, 0), '#2F5D50', null, null, [1.25, 0.8, 0.8]));
    head.add(part(new THREE.ConeGeometry(0.07, 0.36, 4), '#25493F', [0.19, -0.035, 0], [0, 0, -Math.PI / 2 - 0.2]));
    const eyes = [part(new THREE.BoxGeometry(0.03, 0.04, 0.012), '#F3ECDF', [0.04, 0.03, 0.075]), part(new THREE.BoxGeometry(0.03, 0.04, 0.012), '#F3ECDF', [0.04, 0.03, -0.075])];
    eyes.forEach(e => head.add(e));
    const tail = new THREE.Group(); tail.position.set(-0.55, 0.55, 0); body.add(tail);
    tail.add(part(new THREE.ConeGeometry(0.07, 0.9, 4), '#3B7362', [-0.36, 0.27, 0], [0, 0, 0.93]));
    const wingGeo = tris([[0.3, 0, 0], [0.02, 0.46, 0.08], [-0.14, 0.95, 0], [0.02, 0.46, 0.08], [-0.3, 0, 0], [-0.14, 0.95, 0], [0.3, 0, 0], [-0.3, 0, 0], [0.02, 0.46, 0.08]]);
    const wL = new THREE.Group(); wL.position.set(0, 0.62, 0.12); wL.add(mesh(wingGeo, '#8BBFAD', { side: THREE.DoubleSide })); body.add(wL);
    const wR = new THREE.Group(); wR.position.set(0, 0.62, -0.12); wR.add(mesh(wingGeo, '#6BA893', { side: THREE.DoubleSide })); body.add(wR);
    return { root, body, head, eyes, wings: [wL, wR], tail, top: 1.8 };
  }
  function buildFox() {
    const root = new THREE.Group(), body = new THREE.Group(); root.add(body);
    body.add(part(new THREE.ConeGeometry(0.42, 0.95, 4), '#C8693F', [0, 0.475, 0], [0, Math.PI / 4, 0]));
    body.add(part(new THREE.TetrahedronGeometry(0.2, 0), '#F2E3CC', [0.24, 0.48, 0], [0.6, 0.2, 0.9], [0.7, 1.2, 1]));
    const head = new THREE.Group(); head.position.set(0.1, 1.02, 0); body.add(head);
    head.add(part(new THREE.OctahedronGeometry(0.32, 0), '#D9773F', null, null, [1.05, 0.8, 0.95]));
    head.add(part(new THREE.ConeGeometry(0.14, 0.42, 4), '#E8935C', [0.4, -0.06, 0], [Math.PI / 4, 0, -Math.PI / 2]));
    head.add(part(new THREE.OctahedronGeometry(0.05, 0), '#2A2520', [0.62, -0.06, 0]));
    head.add(part(new THREE.ConeGeometry(0.11, 0.34, 3), '#B5542A', [-0.02, 0.32, 0.17], [0.25, 0, 0]));
    head.add(part(new THREE.ConeGeometry(0.11, 0.34, 3), '#B5542A', [-0.02, 0.32, -0.17], [-0.25, 0, 0]));
    const eyes = [part(new THREE.BoxGeometry(0.02, 0.035, 0.08), '#2A2520', [0.27, 0.07, 0.13], [0, -0.5, 0]), part(new THREE.BoxGeometry(0.02, 0.035, 0.08), '#2A2520', [0.27, 0.07, -0.13], [0, 0.5, 0])];
    eyes.forEach(e => head.add(e));
    const tail = new THREE.Group(); tail.position.set(-0.3, 0.2, 0); body.add(tail);
    tail.add(part(new THREE.ConeGeometry(0.16, 0.9, 4), '#B5542A', [-0.36, 0.27, 0], [0, 0, 0.93]));
    tail.add(part(new THREE.ConeGeometry(0.1, 0.26, 4), '#F2E3CC', [-0.82, 0.62, 0], [0, 0, 0.93]));
    return { root, body, head, eyes, tail, top: 1.6 };
  }
  function buildOwl() {
    const root = new THREE.Group(), body = new THREE.Group(); root.add(body);
    body.add(part(new THREE.CylinderGeometry(0.36, 0.46, 0.95, 6), '#8A6A45', [0, 0.475, 0]));
    body.add(part(new THREE.OctahedronGeometry(0.3, 0), '#A7835C', [0.3, 0.42, 0], null, [0.35, 1.05, 0.9]));
    body.add(part(new THREE.TetrahedronGeometry(0.09, 0), '#F7F1E6', [0.34, 0.86, 0]));
    const head = new THREE.Group(); head.position.set(0, 0.95, 0); body.add(head);
    head.add(part(new THREE.CylinderGeometry(0.38, 0.37, 0.52, 6), '#765A3E', [0, 0.26, 0]));
    head.add(part(new THREE.ConeGeometry(0.09, 0.3, 3), '#5E472F', [0, 0.62, 0.25], [0.35, 0, 0]));
    head.add(part(new THREE.ConeGeometry(0.09, 0.3, 3), '#5E472F', [0, 0.62, -0.25], [-0.35, 0, 0]));
    head.add(part(new THREE.CylinderGeometry(0.3, 0.3, 0.04, 6), '#E3D2B4', [0.35, 0.28, 0], [0, 0, Math.PI / 2]));
    head.add(part(new THREE.ConeGeometry(0.05, 0.14, 4), '#D99A3E', [0.42, 0.17, 0], [0, 0, -Math.PI / 2]));
    const eyes = [eyeL, eyeR].map((t, i) => { const e = new THREE.Mesh(new THREE.PlaneGeometry(0.2, 0.2), new THREE.MeshBasicMaterial({ map: t, transparent: true })); e.position.set(0.376, 0.32, i ? -0.12 : 0.12); e.rotation.y = Math.PI / 2; head.add(e); return e; });
    return { root, body, head, eyes, top: 1.8 };
  }
  function buildTurtle() {
    const root = new THREE.Group(), body = new THREE.Group(); root.add(body);
    const shell = new THREE.Group(); shell.position.y = 0.12; body.add(shell);
    shell.add(part(new THREE.SphereGeometry(0.62, 7, 3, 0, Math.PI * 2, 0, Math.PI / 2), '#7D8B4E', null, null, [1, 0.62, 1]));
    shell.add(part(new THREE.CylinderGeometry(0.64, 0.66, 0.08, 7), '#5E6B38'));
    shell.add(part(new THREE.BoxGeometry(0.17, 0.05, 0.14), '#FBF7EF', [0, 0.39, 0]));
    const head = new THREE.Group(); head.position.set(0.72, 0.24, 0); body.add(head);
    head.add(part(new THREE.OctahedronGeometry(0.17, 0), '#8C9C5A', null, null, [1.3, 0.9, 0.9]));
    const eyes = [part(new THREE.BoxGeometry(0.03, 0.04, 0.03), '#2A2520', [0.12, 0.06, 0.08]), part(new THREE.BoxGeometry(0.03, 0.04, 0.03), '#2A2520', [0.12, 0.06, -0.08])];
    eyes.forEach(e => head.add(e));
    [[0.36, 0.36], [0.36, -0.36], [-0.36, 0.36], [-0.36, -0.36]].forEach(([x, z]) => body.add(part(new THREE.ConeGeometry(0.1, 0.28, 4), '#6E7F45', [x, 0.1, z], [0, 0, Math.PI])));
    return { root, body, head, eyes, shell, top: 1.0 };
  }
  function buildBox() {
    const root = new THREE.Group(), body = new THREE.Group(); root.add(body);
    body.add(part(new THREE.BoxGeometry(0.9, 1.05, 0.85), '#C9A877', [0, 0.525, 0]));
    const papers = new THREE.Group(); papers.position.set(0, 1.05, 0); body.add(papers);
    papers.add(part(new THREE.BoxGeometry(0.55, 0.28, 0.02), '#FFFDF8', [0, 0.1, 0.07], [0, 0, 0.12]));
    papers.add(part(new THREE.BoxGeometry(0.5, 0.22, 0.02), '#F4EDE0', [0.05, 0.08, -0.08], [0, 0, -0.1]));
    body.add(part(new THREE.BoxGeometry(0.012, 0.02, 0.78), '#A88553', [0.452, 0.7, 0]));
    body.add(part(new THREE.BoxGeometry(0.012, 0.02, 0.78), '#A88553', [0.452, 0.36, 0]));
    body.add(part(new THREE.BoxGeometry(0.03, 0.06, 0.22), '#7A5A33', [0.465, 0.55, 0]));
    body.add(part(new THREE.BoxGeometry(0.03, 0.06, 0.22), '#7A5A33', [0.465, 0.2, 0]));
    body.add(part(new THREE.BoxGeometry(0.01, 0.12, 0.24), '#FBF7EF', [0.456, 0.2, 0.25]));
    const head = new THREE.Group(); head.position.set(0.46, 0.88, 0); body.add(head);
    const eyes = [part(new THREE.BoxGeometry(0.02, 0.09, 0.06), '#2A2520', [0, 0, 0.16]), part(new THREE.BoxGeometry(0.02, 0.09, 0.06), '#2A2520', [0, 0, -0.16])];
    eyes.forEach(e => head.add(e));
    return { root, body, head, eyes, papers, top: 1.55 };
  }
  function buildFrog() {
    const root = new THREE.Group(), body = new THREE.Group(); root.add(body);
    body.add(part(new THREE.OctahedronGeometry(0.45, 0), '#7FA65A', [0, 0.33, 0], null, [1.05, 0.64, 1]));
    body.add(part(new THREE.OctahedronGeometry(0.3, 0), '#C8D99A', [0.27, 0.28, 0], null, [0.45, 0.8, 0.9]));
    body.add(part(new THREE.BoxGeometry(0.01, 0.02, 0.32), '#2A2520', [0.46, 0.34, 0]));
    body.add(part(new THREE.ConeGeometry(0.13, 0.42, 4), '#5E8C3E', [-0.28, 0.14, 0.38], [0.3, 0, 1.2]));
    body.add(part(new THREE.ConeGeometry(0.13, 0.42, 4), '#4F7A33', [-0.28, 0.14, -0.38], [-0.3, 0, 1.2]));
    const head = new THREE.Group(); head.position.set(0.2, 0.6, 0); body.add(head);
    const pupils = [];
    [0.2, -0.2].forEach(z => {
      head.add(part(new THREE.IcosahedronGeometry(0.14, 0), '#8DB566', [0, 0, z]));
      head.add(part(new THREE.SphereGeometry(0.085, 6, 4), '#FBF7EF', [0.08, 0.04, z]));
      const p = part(new THREE.BoxGeometry(0.035, 0.06, 0.04), '#2A2520', [0.16, 0.04, z]); head.add(p); pupils.push(p);
    });
    return { root, body, head, eyes: pupils, pupils, top: 1.05 };
  }
  const CH = { crane: buildCrane(), fox: buildFox(), owl: buildOwl(), turtle: buildTurtle(), box: buildBox(), frog: buildFrog() };
  CHAR_ORDER.forEach((k, i) => {
    const c = CH[k]; c.key = k; c.root.add(blob(k === 'turtle' ? 1.8 : 1.4)); scene.add(c.root);
    c.yaw = -Math.PI / 2; c.yawBase = -Math.PI / 2; c.speaking = false; c.ph = i * 1.7; c.nextBlink = 1 + Math.random() * 3; c.blinkT = -1; c.shakeT = -9; c.inRound = true;
  });

  // ---------- case folders with turning pages ----------
  const kraftMat = M('#C9A877'), insideMat = M('#E9DCC3');
  function buildPage(caseId, i) {
    const seg = lowFX ? 14 : 24;
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array((seg + 1) * 2 * 3), uv = new Float32Array((seg + 1) * 2 * 2), idx = [];
    for (let s = 0; s <= seg; s++) { uv[s * 4] = s / seg; uv[s * 4 + 1] = 1; uv[s * 4 + 2] = s / seg; uv[s * 4 + 3] = 0; if (s < seg) { const b0 = 2 * s, f0 = 2 * s + 1, b1 = 2 * s + 2, f1 = 2 * s + 3; idx.push(b0, f0, b1, b1, f0, f1); } }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); geo.setIndex(idx);
    const frontTex = canvasTex(1024, 1296, pageFrontDraw(CASES[caseId], i));
    const backTex = canvasTex(1024, 1296, pageBackDraw(i, null, null));
    const front = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: frontTex, side: THREE.FrontSide }));
    const back = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: backTex, side: THREE.BackSide }));
    front.receiveShadow = back.receiveShadow = true; front.castShadow = true;
    const g = new THREE.Group(); g.add(front); g.add(back);
    const page = { group: g, geo, seg, t: 0, i, yR: 0.066 + (2 - i) * 0.012, yL: 0.066 + i * 0.012, frontTex, backTex };
    updatePage(page); return page;
  }
  function updatePage(p) {
    const a = Math.PI * p.t, k = Math.sin(Math.PI * p.t) * 1.1 / PW, ds = (PW - 0.12) / p.seg, baseY = p.yR + (p.yL - p.yR) * p.t;
    const pos = p.geo.attributes.position; let x = 0, y = 0;
    for (let s = 0; s <= p.seg; s++) {
      if (s > 0) { const phi = Math.max(0, Math.min(Math.PI, a - k * (s - 0.5) * ds)); x += Math.cos(phi) * ds; y += Math.sin(phi) * ds; }
      pos.setXYZ(2 * s, x, baseY + y, -PD / 2 + 0.12); pos.setXYZ(2 * s + 1, x, baseY + y, PD / 2 - 0.12);
    }
    pos.needsUpdate = true; p.geo.computeVertexNormals(); p.geo.computeBoundingSphere();
  }
  function buildFolder(caseId) {
    const g = new THREE.Group();
    const base = new THREE.Mesh(new THREE.BoxGeometry(PW, 0.06, PD), [kraftMat, kraftMat, insideMat, kraftMat, kraftMat, kraftMat]);
    base.position.set(PW / 2, 0.03, 0); base.castShadow = base.receiveShadow = true; g.add(base);
    g.add(part(new THREE.BoxGeometry(1.6, 0.06, 0.5), '#B08F5E', [PW - 1.1, 0.03, -PD / 2 - 0.22]));
    const pivot = new THREE.Group(); g.add(pivot);
    const cover = new THREE.Mesh(new THREE.BoxGeometry(PW, 0.06, PD), [kraftMat, kraftMat, insideMat, kraftMat, kraftMat, kraftMat]);
    cover.position.set(-PW / 2, 0.03, 0); cover.castShadow = cover.receiveShadow = true; pivot.add(cover);
    const coverTex = canvasTex(1024, 1296, coverDraw(CASES[caseId], null));
    const label = new THREE.Mesh(new THREE.PlaneGeometry(PW * 0.985, PD * 0.985), new THREE.MeshLambertMaterial({ map: coverTex }));
    label.position.set(-PW / 2, -0.003, 0); label.rotation.set(Math.PI / 2, 0, Math.PI); pivot.add(label);
    const pages = [0, 1, 2].map(i => { const p = buildPage(caseId, i); g.add(p.group); return p; });
    const f = { caseId, group: g, pivot, coverTex, pages, open: 0, hover: 0, hoverT: 0, imprint: null };
    setOpen(f, 0);
    g.traverse(o => { o.userData.caseId = caseId; });
    scene.add(g); return f;
  }
  function setOpen(f, v) { f.open = v; f.pivot.rotation.z = -Math.PI * (1 - v); f.pivot.position.y = 0.135 * (1 - v); }
  let vw = 1, vh = 1;
  const isNarrow = () => vw / vh < 1;
  const titleF = (id) => isNarrow() ? (id === 'priya' ? [-3.25, 0, -1.3] : [0.25, 0, -1.3]) : (id === 'priya' ? [-4.4, 0, -1.4] : [0.7, 0, -1.4]);
  const titleScale = () => isNarrow() ? 0.5 : 0.62;
  const folders = { priya: buildFolder('priya'), nadia: buildFolder('nadia') };
  const folderHits = []; Object.values(folders).forEach(f => f.group.traverse(o => { if (o.isMesh) folderHits.push(o); }));

  // ---------- pop-up dioramas ----------
  function accordion(width, height, n, color) {
    const p = [];
    for (let i = 0; i < n; i++) { const x0 = -width / 2 + i * width / n, x1 = x0 + width / n, z0 = (i % 2) * 0.16, z1 = ((i + 1) % 2) * 0.16; p.push([x0, 0, z0], [x1, 0, z1], [x1, height, z1], [x0, 0, z0], [x1, height, z1], [x0, height, z0]); }
    return mesh(tris(p), color, { side: THREE.DoubleSide });
  }
  function makeDio() { const g = new THREE.Group(); g.position.copy(O); scene.add(g); return { group: g, pieces: [], refs: {} }; }
  function piece(d, hingePos, flat) { const h = new THREE.Group(); h.position.set(hingePos[0], hingePos[1], hingePos[2]); h.userData.flat = !!flat; d.group.add(h); d.pieces.push(h); h.visible = false; return h; }
  function plane(tex, w, h, basic) { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), basic ? new THREE.MeshBasicMaterial({ map: tex, transparent: true }) : new THREE.MeshLambertMaterial({ map: tex, transparent: true })); m.receiveShadow = true; return m; }

  // courtroom
  const court = makeDio();
  { const d = court;
    const wall = piece(d, [0, 0, -2.75]); wall.add(accordion(5.4, 2.4, 10, '#EADFCB'));
    const em = plane(emblemTex, 0.62, 0.62, true); em.position.set(0, 2.05, 0.2); wall.add(em);
    [-2.35, 2.35].forEach(x => { const pl = piece(d, [x, 0, -2.3]); pl.add(part(new THREE.CylinderGeometry(0.17, 0.2, 2.0, 6), '#F1E8D8', [0, 1.0, 0])); });
    const rug = piece(d, [0, 0, 0], true); rug.add(part(new THREE.BoxGeometry(4.4, 0.012, 2.2), '#E3D4B7', [0, 0.006, 1.45]));
    const bench = piece(d, [0, 0, -1.0]);
    bench.add(part(new THREE.BoxGeometry(2.7, 0.95, 0.8), '#8A6A45', [0, 0.475, -0.42]));
    bench.add(part(new THREE.BoxGeometry(2.9, 0.06, 0.95), '#7A5A33', [0, 0.98, -0.42]));
    bench.add(part(new THREE.BoxGeometry(2.4, 0.66, 0.02), '#A3824F', [0, 0.46, -0.01]));
    bench.add(part(new THREE.CylinderGeometry(0.12, 0.14, 0.05, 8), '#5E472F', [0.3, 1.035, -0.25]));
    const gav = new THREE.Group(); gav.position.set(0.85, 1.07, -0.25); gav.rotation.z = -0.9; bench.add(gav);
    gav.add(part(new THREE.CylinderGeometry(0.035, 0.04, 0.55, 6), '#A06B42', [-0.28, 0, 0], [0, 0, Math.PI / 2]));
    gav.add(part(new THREE.CylinderGeometry(0.09, 0.09, 0.32, 6), '#7A4E2E', [-0.55, 0, 0], [Math.PI / 2, 0, 0]));
    d.refs.gavel = gav;
    const shr = piece(d, [-2.3, 0, -0.35]);
    const shrBody = new THREE.Group(); shr.add(shrBody);
    shrBody.add(part(new THREE.BoxGeometry(0.85, 0.8, 0.62), '#6B5E50', [0, 0.4, -0.31]));
    shrBody.add(part(new THREE.BoxGeometry(0.62, 0.02, 0.07), '#1F1A15', [0, 0.81, -0.31]));
    shrBody.add(part(new THREE.BoxGeometry(0.62, 0.07, 0.02), '#1F1A15', [0, 0.1, 0.005]));
    d.refs.shredder = shrBody; d.refs.shredderPos = new V3(-2.3, 0, -0.66);
  }
  // switchboard
  const call = makeDio();
  const lampMat = new THREE.MeshLambertMaterial({ color: '#5E472F', emissive: '#000000', flatShading: true });
  { const d = call;
    const wall = piece(d, [0, 0, -2.75]); wall.add(accordion(5.4, 2.4, 10, '#E6DCCB'));
    const sb = piece(d, [0, 0, -1.72]);
    sb.add(part(new THREE.BoxGeometry(2.7, 1.9, 0.34), '#8B6B45', [0, 0.95, -0.17]));
    sb.add(part(new THREE.BoxGeometry(2.5, 1.5, 0.02), '#6E5236', [0, 0.98, 0.01]));
    for (let r = 0; r < 3; r++) for (let c = 0; c < 6; c++) sb.add(part(new THREE.CylinderGeometry(0.055, 0.055, 0.03, 6), '#1F1A15', [-0.95 + c * 0.38, 0.55 + r * 0.4, 0.03], [Math.PI / 2, 0, 0]));
    for (let c = 0; c < 6; c++) { const l = new THREE.Mesh(new THREE.SphereGeometry(0.055, 6, 4), lampMat); l.position.set(-0.95 + c * 0.38, 1.66, 0.04); sb.add(l); }
    const lab = plane(boardLabelTex, 1.7, 0.25, true); lab.position.set(0, 2.1, -0.05); sb.add(lab);
  }
  const cablePts = [[-1.02, 1.4, 1.16], [-0.95, 2.3, 0.35], [-0.57, 1.33, -1.66], [0.55, 2.25, -0.55], [1.78, 1.3, 0.62]].map(p => new V3(p[0], p[1], p[2]).add(O));
  const cableCurve = new THREE.CatmullRomCurve3(cablePts);
  const CABLE_SEG = 140, CABLE_RAD = 5;
  const cableMat = new THREE.MeshLambertMaterial({ color: '#EADCC2', emissive: '#2F5D50', emissiveIntensity: 0, flatShading: true });
  const cable = new THREE.Mesh(new THREE.TubeGeometry(cableCurve, CABLE_SEG, 0.045, CABLE_RAD, false), cableMat);
  cable.castShadow = true; cable.visible = false; scene.add(cable);
  const plug = part(new THREE.CylinderGeometry(0.07, 0.07, 0.18, 6), '#2F5D50'); plug.visible = false; scene.add(plug);
  // letter + guardian strip
  const letter = new THREE.Group(); letter.position.copy(O).add(new V3(0, 2.25, 0.55)); letter.visible = false; scene.add(letter);
  const sheet = plane(letterTex, 2.5, 1.758); sheet.castShadow = true; letter.add(sheet);
  const backing = part(new THREE.BoxGeometry(2.5, 1.758, 0.01), '#F4EDE0', [0, 0, -0.008]); letter.add(backing);
  const hoursStrip = plane(hoursTex, 2.5, 0.2); hoursStrip.position.set(0, -0.27, 0.004); letter.add(hoursStrip);
  const strike = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.035, 0.012).translate(0.5, 0, 0), new THREE.MeshBasicMaterial({ color: '#B5503E' }));
  strike.position.set(-1.12, -0.27, 0.012); strike.scale.x = 0.0001; hoursStrip.add(strike); strike.position.set(-1.12, 0, 0.008);
  const planeGeo = tris([[0.6, 0, 0], [-0.4, 0.04, 0.42], [-0.4, 0.04, 0], [0.6, 0, 0], [-0.4, 0.04, 0], [-0.4, 0.04, -0.42], [0.6, 0, 0], [-0.4, 0.04, 0], [-0.4, -0.16, 0]]);
  const paperPlane = mesh(planeGeo, '#FFFDF8', { side: THREE.DoubleSide }); paperPlane.visible = false; scene.add(paperPlane);
  // vault
  const vault = makeDio();
  { const d = vault;
    const wall = piece(d, [0, 0, -2.75]); wall.add(accordion(5.4, 2.4, 10, '#E4D9C6'));
    const fr = piece(d, [0.3, 0, -1.85]);
    fr.add(part(new THREE.BoxGeometry(3.3, 2.85, 0.4), '#B9A47F', [0, 1.425, -0.2]));
    fr.add(part(new THREE.CylinderGeometry(1.22, 1.22, 0.02, 8), '#2E2620', [0, 1.4, 0.006], [Math.PI / 2, 0, 0]));
    const door = new THREE.Group(); door.position.set(-1.22, 1.4, 0.05); fr.add(door);
    door.add(part(new THREE.CylinderGeometry(1.18, 1.18, 0.24, 8), '#C7B38E', [1.22, 0, 0.12], [Math.PI / 2, 0, 0]));
    door.add(part(new THREE.TorusGeometry(1.0, 0.05, 4, 8), '#A38D66', [1.22, 0, 0.25]));
    const wheel = new THREE.Group(); wheel.position.set(1.22, 0, 0.31); door.add(wheel);
    wheel.add(part(new THREE.TorusGeometry(0.48, 0.06, 4, 8), '#7A5A33'));
    for (let k = 0; k < 3; k++) wheel.add(part(new THREE.BoxGeometry(0.96, 0.07, 0.07), '#7A5A33', [0, 0, 0], [0, 0, k * Math.PI / 3]));
    wheel.add(part(new THREE.CylinderGeometry(0.12, 0.12, 0.12, 6), '#5E472F', [0, 0, 0.02], [Math.PI / 2, 0, 0]));
    d.refs.door = door; d.refs.wheel = wheel;
  }
  const bank = new THREE.Group(); bank.position.copy(O).add(new V3(1.95, 1.6, 0.95)); bank.rotation.x = -0.2; bank.visible = false; scene.add(bank);
  bank.add(part(new THREE.BoxGeometry(1.5, 0.95, 0.04), '#2F5D50'));
  const bankFront = plane(bankFrontTex, 1.48, 0.925); bankFront.position.z = 0.022; bank.add(bankFront);
  const bankBack = plane(bankBackTex, 1.48, 0.925); bankBack.position.z = -0.022; bankBack.rotation.y = Math.PI; bank.add(bankBack);
  const coin = part(new THREE.CylinderGeometry(0.22, 0.22, 0.05, 8), '#D9B867', null, [Math.PI / 2, 0, 0]); coin.visible = false; scene.add(coin);
  const DIOS = [court, call, vault];
  const ROUND_IDS = ['hearing', 'call', 'money'];

  // stamp tool
  const stampTool = new THREE.Group(); stampTool.visible = false; scene.add(stampTool);
  stampTool.add(part(new THREE.BoxGeometry(1, 0.2, 0.55), '#5E472F', [0, 0.15, 0]));
  const rubber = new THREE.Mesh(new THREE.BoxGeometry(0.96, 0.05, 0.5), M('#2F5D50')); rubber.position.y = 0.025; stampTool.add(rubber);
  stampTool.add(part(new THREE.CylinderGeometry(0.09, 0.12, 0.55, 6), '#8A6A45', [0, 0.52, 0]));
  stampTool.add(part(new THREE.SphereGeometry(0.17, 6, 4), '#A06B42', [0, 0.84, 0]));

  // dust
  let dust = null;
  if (!lowFX && !reduce) {
    const N = 150, p = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) { p[i * 3] = -3 + Math.random() * 12; p[i * 3 + 1] = 0.3 + Math.random() * 5; p[i * 3 + 2] = -4 + Math.random() * 8.5; }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    dust = new THREE.Points(g, new THREE.PointsMaterial({ map: dotTex, size: 0.07, transparent: true, depthWrite: false, opacity: 0.75, color: '#FFF6E2' }));
    scene.add(dust);
  }

  // ---------- dynamic state ----------
  let dyn = [];
  const st = { phase: null, caseId: 'priya', roundId: 'hearing', ri: 0, speaker: null, held: {}, objCards: {}, fan: {}, live: false, stall: false, watching: false, ringT: 0, camMode: 'title', hover: null, labelEls: null, inset: 0, sel: null };
  function addDyn(o, parent) { (parent || scene).add(o); dyn.push(o); return o; }
  function removeObj(o) { if (!o) return; if (o.parent) o.parent.remove(o); }
  function resetDynamic() {
    dyn.forEach(removeObj); dyn = [];
    st.held = {}; st.objCards = {}; st.fan = {}; st.live = false; st.stall = false; st.watching = false;
    letter.visible = false; letter.scale.setScalar(1); letter.rotation.set(-0.35, 0, 0); hoursStrip.visible = true; hoursStrip.position.set(0, -0.27, 0.004); hoursStrip.scale.setScalar(1); strike.scale.x = 0.0001;
    cable.visible = false; cable.geometry.setDrawRange(0, 0); cableMat.emissiveIntensity = 0; plug.visible = false; paperPlane.visible = false; coin.visible = false;
    vault.refs.door.rotation.y = 0; vault.refs.wheel.rotation.z = 0; bank.visible = false; bank.rotation.set(-0.2, 0, 0); redraw(bankBackTex, bankBackDraw(0, false, curCase().employer));
    CH.turtle.shell.position.y = 0.12; CH.turtle.shell.rotation.set(0, 0, 0); court.refs.gavel.rotation.z = -0.9; stampTool.visible = false;
    DIOS.forEach(d => d.pieces.forEach(h => { h.visible = false; h.rotation.x = h.userData.flat ? 0 : -Math.PI / 2; h.scale.setScalar(h.userData.flat ? 0.001 : 1); }));
  }
  function worldOf(o, local) { const v = local ? local.clone() : new V3(); return o.localToWorld(v); }
  function charTop(k, extra) { const c = CH[k]; return c.root.position.clone().add(new V3(0, c.top * c.root.scale.y + (extra || 0), 0)); }

  // ---------- characters placement ----------
  function hop(c, to, scale, yaw, delay, instant) {
    if (instant) { c.root.position.copy(to); c.root.scale.setScalar(scale); c.yawBase = yaw; c.yaw = yaw; c.root.rotation.y = yaw; return; }
    const dist = c.root.position.distanceTo(to);
    moveTo(c.root, to.clone(), { dur: 0.6 + Math.min(0.6, dist * 0.05), delay, arc: dist > 0.2 ? Math.min(2.4, 0.7 + dist * 0.12) : 0, scale, ease: EASE.inOut, onStart() { c.yawBase = yaw; } });
  }
  function placeChars(mode, roundId, delay, instant) {
    CHAR_ORDER.forEach((k, i) => {
      const c = CH[k]; let to, s = 1, yaw = -Math.PI / 2;
      if (mode === 'title') { to = isNarrow() ? new V3(-2.75 + i * 1.1, 0, 2.5) : new V3(-5.25 + i * 2.1, 0, 3.7); s = isNarrow() ? 0.8 : 0.95; c.inRound = true; }
      else if (mode === 'results') { to = new V3(0.35 + i * 1.08, 0, 4.55); s = 0.78; c.inRound = false; }
      else { const sl = SLOTS[roundId][k]; if (sl) { to = new V3(sl[0], sl[1], sl[2]).add(O); yaw = sl[3]; c.inRound = true; } else { to = new V3(0.2 + i * 1.3, 0, -5.4); s = 0.72; c.inRound = false; } }
      hop(c, to, s, yaw, (delay || 0) + i * 0.07, instant);
    });
  }
  function setSpeaker(who) { st.speaker = who; CHAR_ORDER.forEach(k => { CH[k].speaking = k === who; }); }

  // ---------- pop-up ----------
  function popUp(d, delay) {
    d.pieces.forEach((h, i) => tw({ dur: 0.75, delay: delay + i * 0.08, ease: EASE.back,
      start() { h.visible = true; }, update(e) { if (h.userData.flat) h.scale.setScalar(Math.max(0.001, e)); else { h.rotation.x = -Math.PI / 2 * (1 - e); h.scale.setScalar(1); } } }));
  }
  function popDown(d, delay) {
    d.pieces.slice().reverse().forEach((h, i) => tw({ dur: 0.45, delay: delay + i * 0.04, ease: EASE.in,
      update(e) { if (h.userData.flat) h.scale.setScalar(Math.max(0.001, 1 - e)); else h.rotation.x = -Math.PI / 2 * e; }, done() { h.visible = false; } }));
  }
  function turnPage(f, i, to, delay, dur) { const p = f.pages[i]; let from; tw({ dur: dur || 1.5, delay, ease: EASE.inOut, start() { from = p.t; }, update(e) { p.t = from + (to - from) * e; updatePage(p); } }); }

  // ---------- cards ----------
  function makeCard(tex, scale) {
    const g = new THREE.Group(); g.scale.setScalar(scale || 1);
    const b = new THREE.Mesh(new THREE.BoxGeometry(0.74, 0.016, 0.98), M('#EFE6D4')); b.castShadow = true; b.receiveShadow = true; g.add(b);
    const face = new THREE.Mesh(new THREE.PlaneGeometry(0.725, 0.965), new THREE.MeshLambertMaterial({ map: tex })); face.rotation.x = -Math.PI / 2; face.position.y = 0.0085; face.receiveShadow = true; g.add(face);
    return addDyn(g);
  }
  function popIn(o, s) { o.scale.setScalar(0.001); tw({ dur: 0.45, ease: EASE.back, update(e) { o.scale.setScalar(Math.max(0.001, (s || 1) * e)); } }); }
  function fadeAway(o, delay) { let s0; tw({ dur: 0.45, delay: delay || 0, ease: EASE.in, start() { s0 = o.scale.x; }, update(e) { o.scale.setScalar(Math.max(0.001, s0 * (1 - e))); }, done() { removeObj(o); } }); }
  function burst(at, n, color) {
    for (let i = 0; i < (lowFX ? Math.ceil(n / 2) : n); i++) {
      const b = addDyn(part(new THREE.TetrahedronGeometry(0.06, 0), color || ['#FBF7EF', '#E9DCC3', '#C9A877'][i % 3]));
      const dir = new V3(Math.random() - 0.5, Math.random() * 0.8 + 0.2, Math.random() - 0.5).normalize(), p0 = at.clone();
      tw({ dur: 0.8, ease: EASE.out, update(e, k) { b.position.copy(p0).addScaledVector(dir, e * 0.9); b.position.y -= k * k * 0.9; b.rotation.set(k * 6, k * 4, 0); b.scale.setScalar(Math.max(0.001, 1 - k)); }, done() { removeObj(b); } });
    }
  }
  function imprintMesh(text, color, w) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w * 340 / 1024), new THREE.MeshBasicMaterial({ map: stampTex(text, color), transparent: true, opacity: 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
    return m;
  }
  function stampAt(pos, imprint, scl, color, delay) {
    const h0 = 3.2 * scl + 1.2;
    tw({ dur: 0.42, delay, ease: EASE.in, start() { stampTool.visible = true; stampTool.scale.setScalar(scl); rubber.material = M(color); stampTool.position.set(pos.x, pos.y + h0, pos.z); stampTool.rotation.set(0, 0.12, 0); }, update(e) { stampTool.position.y = pos.y + h0 * (1 - e) + 0.01; } });
    tw({ dur: 0.18, delay: delay + 0.42, ease: EASE.out, start() { shake(0.05 + 0.07 * scl); }, update(e) { stampTool.scale.y = scl * (1 - 0.2 * Math.sin(Math.PI * e)); imprint.material.opacity = 0.93 * e; } });
    tw({ dur: 0.55, delay: delay + 0.62, ease: EASE.inOut, update(e) { stampTool.position.y = pos.y + 0.01 + e * (h0 + 1); stampTool.position.x = pos.x + e * 1.4; }, done() { stampTool.visible = false; stampTool.scale.setScalar(scl); imprint.material.opacity = 0.93; } });
  }
  function slam(delay) {
    const gv = court.refs.gavel;
    tw({ dur: 0.3, delay: delay || 0, ease: EASE.out, update(e) { gv.rotation.z = -0.4 - 0.65 * e; } });
    tw({ dur: 0.14, delay: (delay || 0) + 0.3, ease: EASE.in, update(e) { gv.rotation.z = -1.05 + 1.1 * e; }, done() { shake(0.22); burst(worldOf(gv, new V3(-0.55, -0.05, 0)), 6, '#E9DCC3'); } });
    tw({ dur: 0.5, delay: (delay || 0) + 0.44, ease: EASE.out, update(e) { gv.rotation.z = 0.05 - 0.95 * e; } });
  }

  // ---------- hearing actions ----------
  const AIR = () => O.clone().add(new V3(0.1, 1.95, 0.6));
  const SLOT = (n) => O.clone().add(new V3(-1.95 + (n - 1) * 1.3, 0.02, 2.55));
  function holdDraft() {
    if (st.held.draft) return;
    const c = makeCard(cardTex('draft', 'DRAFT QUOTE · AI', '“' + DRAFT + '”', 'Cites: IRS Publication 519'), 1);
    c.position.copy(charTop('crane', 0.55)).add(new V3(0.25, 0, 0.1)); c.rotation.set(0.9, 0, -0.1); popIn(c, 1); st.held.draft = c;
  }
  function shredFx() {
    const c = st.held.draft || (holdDraft(), st.held.draft); st.held.draft = null;
    const sp = O.clone().add(court.refs.shredderPos), slot = sp.clone().add(new V3(0, 1.45, 0));
    moveTo(c, slot, { dur: 0.8, arc: 0.6, rot: [1.5708, 0, 0], ease: EASE.inOut });
    tw({ dur: 1.0, delay: 0.85, ease: EASE.in, update(e) { c.position.y = slot.y - e * 0.9; st.shredding = e < 1; }, done() { removeObj(c); st.shredding = false; } });
    const tex = c.children[1].material.map;
    for (let i = 0; i < (lowFX ? 6 : 9); i++) {
      const n = lowFX ? 6 : 9, t = tex.clone(); t.repeat.set(1 / n, 1); t.offset.set(i / n, 0); t.needsUpdate = true;
      const s = addDyn(new THREE.Mesh(new THREE.PlaneGeometry(0.74 / n, 0.9), new THREE.MeshLambertMaterial({ map: t, side: THREE.DoubleSide })));
      s.castShadow = true; s.visible = false;
      const from = sp.clone().add(new V3(-0.25 + i * 0.06, 0.12, 0.34)), to = sp.clone().add(new V3(-0.7 + Math.random() * 1.4, 0.015 + i * 0.002, 0.75 + Math.random() * 0.75));
      s.position.copy(from);
      moveTo(s, to, { dur: 0.75, delay: 1.25 + i * 0.09, arc: 0.25, rot: [-Math.PI / 2, 0, (Math.random() - 0.5) * 2.4], ease: EASE.out, onStart() { s.visible = true; s.rotation.set(0, 0, 0); } });
    }
  }
  function verifyFx() {
    const c = makeCard(cardTex('quote', 'OFFICIAL SOURCE · IRS.gov', '“' + P519.quote + '”', 'IRS Publication 519 (2025)'), 1);
    c.position.copy(charTop('crane', 0.55)).add(new V3(0.25, 0, 0.1)); c.rotation.set(0.9, 0, 0); popIn(c, 1);
    moveTo(c, O.clone().add(new V3(-0.55, 1.05, -1.15)), { dur: 1.0, delay: 0.7, arc: 0.9, rot: [0, 0.25, 0], spins: 1, ease: EASE.inOut });
  }
  function foxThrow(n, label) {
    const c = makeCard(cardTex('objection', 'OBJECTION ' + n, label), 1);
    c.position.copy(CH.fox.root.position).add(new V3(-0.35, 1.15, 0.1)); c.rotation.set(0.5, 0, 0.4); st.objCards[n] = c;
    moveTo(c, AIR(), { dur: 0.85, arc: 0.6, rot: [0.9, 0, 0], spins: 1, ease: EASE.out, onDone() { c.userData.hover = true; c.userData.hoverBase = AIR(); } });
    tw({ dur: 0.4, ease: EASE.out, update(e) { CH.fox.body.rotation.z = Math.sin(Math.PI * e) * 0.25; } });
  }
  function craneCollide(n, title, from) {
    const ob = st.objCards[n];
    const c = from || makeCard(cardTex('evidence', 'EVIDENCE', title), 1);
    if (!from) { c.position.copy(charTop('crane', 0.4)); c.rotation.set(0.9, 0, 0); }
    const meet = AIR().add(new V3(-0.12, 0, 0.06));
    moveTo(c, meet, { dur: 0.75, arc: 0.45, rot: [0.9, 0, 0.12], spins: 1, ease: EASE.in, onDone() {
      shake(0.08); burst(meet, 10);
      if (ob) { ob.userData.hover = false; moveTo(ob, SLOT(n), { dur: 0.85, arc: 0.35, rot: [0, (Math.random() - 0.5) * 0.3, 0], spins: 1, ease: EASE.out }); }
      moveTo(c, SLOT(n).add(new V3(0.26, 0.02, -0.3)), { dur: 0.9, arc: 0.4, rot: [0, 0.45, 0], spins: -1, ease: EASE.out });
    } });
    tw({ dur: 0.4, ease: EASE.out, update(e) { CH.crane.wings.forEach((w, i) => { w.rotation.x = (i ? -1 : 1) * (0.5 + Math.sin(Math.PI * e) * 0.8); }); } });
  }
  function stampCard(n, s) {
    const card = st.objCards[n]; if (!card) return;
    const col = s === 'overruled' ? '#2F5D50' : '#B5503E';
    const im = imprintMesh(s.toUpperCase(), col, 0.66); im.rotation.set(-Math.PI / 2, 0, 0.14); im.position.set(0, 0.012, 0.15); card.add(im);
    stampAt(SLOT(n), im, 0.42, col, 0.75);
  }
  function verdictStamp(text) {
    const col = text === 'UPHELD' ? '#2F5D50' : '#B5503E';
    const im = addDyn(imprintMesh(text, col, 2.7)); im.rotation.set(-Math.PI / 2, 0, 0.1); im.position.copy(O).add(new V3(0, 0.03, 0.45));
    stampAt(im.position.clone(), im, 1.25, col, 0.75);
  }

  // ---------- fan of choice cards (argue mode) ----------
  function showFan(s) {
    clearFan(true);
    const who = s.beat.who, opts = s.beat.choice.options;
    opts.forEach((o, i) => {
      const c = makeCard(cardTex('evidence', 'EVIDENCE CARD', o.title), 0.78);
      c.position.copy(charTop(who, 0.6)).add(new V3(-0.62 + i * 0.62, i === 1 ? 0.12 : 0, 0.25)); c.rotation.set(0.9, 0, (1 - i) * 0.15);
      c.userData.hover = true; c.userData.hoverBase = c.position.clone(); popIn(c, 0.78); st.fan[o.id] = c;
    });
  }
  function clearFan(instant, keep) { Object.keys(st.fan).forEach(id => { if (id === keep) return; const c = st.fan[id]; if (instant) removeObj(c); else fadeAway(c); }); st.fan = {}; }
  function wrongPick(s, id) {
    if (s.beat.choice.approval) { const a = st.approvalCard; if (a) { let z0; tw({ dur: 0.5, ease: EASE.lin, start() { z0 = a.rotation.y; }, update(e, k) { a.rotation.y = z0 + Math.sin(k * 18) * 0.12 * (1 - k); } }); } return; }
    const c = st.fan[id]; delete st.fan[id];
    const who = s.beat.who; const ch = CH[who]; ch.shakeT = performance.now() / 1000;
    if (!c) return;
    c.userData.hover = false;
    const to = ch.root.position.clone().add(new V3(1.0 + Math.random() * 0.4, 0.02, 0.7));
    const tex = cardTex('wrong', 'NOT ADMISSIBLE', s.beat.choice.options.find(o => o.id === id).title); c.children[1].material = new THREE.MeshLambertMaterial({ map: tex });
    moveTo(c, to, { dur: 0.8, arc: 0.5, rot: [0, 0.6, 0.2], spins: 1, ease: EASE.out, onDone() { fadeAway(c, 0.6); } });
  }
  function resolveChoice(s, id) {
    if (s.beat.choice.approval) { approvalFx(s, true); return; }
    const opt = s.beat.choice.options.find(o => o.id === id) || s.beat.choice.options.find(o => o.correct);
    const card = st.fan[opt.id]; if (card) { delete st.fan[opt.id]; card.userData.hover = false; }
    clearFan(false);
    if (s.roundId === 'hearing') { craneCollide(s.objN || 1, opt.title, card || null); return; }
    const c = card || makeCard(cardTex('evidence', 'EVIDENCE', opt.title), 0.78);
    if (!card) { c.position.copy(charTop(s.beat.who, 0.5)); c.rotation.set(0.9, 0, 0); popIn(c, 0.78); }
    const target = s.roundId === 'money' ? bank.position.clone() : letter.position.clone();
    moveTo(c, target, { dur: 0.8, delay: card ? 0 : 0.3, arc: 0.6, rot: [0.9, 0, 0], spins: 1, ease: EASE.inOut, onDone() { burst(target, 8); fadeAway(c); if (s.roundId === 'money') matchFx(); } });
  }

  function curCase() { return st.case || CASES.priya; }
  function approvalFx(s, approved) {
    let card = st.approvalCard;
    if (!card || card.userData.beatKey !== s.ri + '-' + s.bi) {
      const cs = curCase();
      card = makeCard(cardTex('approval', 'NEEDS ' + cs.first.toUpperCase() + '’S OK', s.beat.choice.approvalTitle), 1.25);
      card.position.copy(O).add(new V3(st.approvals % 2 ? 1.05 : -0.75, 0.03, 2.45)); card.rotation.set(0, st.approvals % 2 ? -0.08 : 0.08, 0);
      card.userData.beatKey = s.ri + '-' + s.bi; st.approvals += 1; st.approvalCard = card; popIn(card, 1.25);
    }
    if (approved && !card.userData.approved) {
      card.userData.approved = true;
      const im = imprintMesh('APPROVED', '#2F5D50', 0.68); im.rotation.set(-Math.PI / 2, 0, -0.12); im.position.set(0, 0.012, 0.18); card.add(im);
      stampAt(card.position.clone(), im, 0.55, '#2F5D50', 0.55);
    }
  }
  // ---------- call actions ----------
  function plugCable() {
    cable.visible = true; plug.visible = true;
    tw({ dur: 1.7, ease: EASE.inOut, update(e) { cable.geometry.setDrawRange(0, Math.floor(e * CABLE_SEG) * CABLE_RAD * 6); const p = cableCurve.getPointAt(Math.min(0.999, e)), q = cableCurve.getPointAt(Math.min(1, e + 0.01)); plug.position.copy(p); plug.lookAt(q); plug.rotateX(Math.PI / 2); }, done() { st.live = true; shake(0.04); } });
  }
  function showLetter() {
    letter.visible = true;
    tw({ dur: 0.8, ease: EASE.back, update(e) { letter.scale.setScalar(Math.max(0.001, e)); letter.rotation.x = -1.6 + 1.25 * e; letter.rotation.y = (1 - e) * 0.6; } });
  }
  function blockFx() {
    if (!letter.visible) { letter.visible = true; letter.scale.setScalar(1); letter.rotation.set(-0.35, 0, 0); }
    const t = CH.turtle; hop(t, O.clone().add(new V3(0, 0, 1.0)), 1, -Math.PI / 2, 0);
    tw({ dur: 0.5, delay: 0.55, ease: EASE.back, update(e) { t.shell.position.y = 0.12 + e * 0.42; t.shell.rotation.x = -e * 0.35; t.body.position.y = e * 0.08; } });
    tw({ dur: 0.55, delay: 1.05, ease: EASE.inOut, update(e) { strike.scale.x = Math.max(0.0001, e * 2.24); } });
    let p0;
    tw({ dur: 0.8, delay: 1.9, ease: EASE.in, start() { p0 = hoursStrip.position.clone(); }, update(e, k) {
      const tgt = letter.worldToLocal(worldOf(t.shell, new V3(0, 0.3, 0)));
      hoursStrip.position.lerpVectors(p0, tgt, e); hoursStrip.position.z += Math.sin(Math.PI * k) * 0.4; hoursStrip.scale.setScalar(Math.max(0.001, 1 - e * 0.95)); hoursStrip.rotation.z = e * 0.6; },
      done() { hoursStrip.visible = false; burst(worldOf(t.shell, new V3(0, 0.5, 0)), 6, '#B5503E'); } });
    tw({ dur: 0.5, delay: 2.8, ease: EASE.inOut, update(e) { t.shell.position.y = 0.54 - e * 0.42; t.shell.rotation.x = -0.35 * (1 - e); } });
  }
  function sendFx() {
    hoursStrip.visible = false; const from = letter.position.clone();
    tw({ dur: 0.55, ease: EASE.in, update(e) { letter.scale.set(Math.max(0.001, 1 - e), Math.max(0.001, 1 - e * 0.98), 1); letter.rotation.y = e * Math.PI; }, done() { letter.visible = false; } });
    const boxTop = CH.box.root.position.clone().add(new V3(0, 1.35, 0));
    const path = new THREE.CatmullRomCurve3([from, from.clone().lerp(boxTop, 0.5).add(new V3(0, 1.2, 0.5)), boxTop]);
    tw({ dur: 0.35, delay: 0.45, ease: EASE.back, start() { paperPlane.visible = true; paperPlane.position.copy(from); }, update(e) { paperPlane.scale.setScalar(Math.max(0.001, e)); } });
    tw({ dur: 1.5, delay: 0.85, ease: EASE.inOut, update(e) { const p = path.getPointAt(Math.min(0.999, e)), q = path.getPointAt(Math.min(1, e + 0.02)); paperPlane.position.copy(p); paperPlane.lookAt(q); paperPlane.rotateY(-Math.PI / 2); paperPlane.rotateX(Math.sin(e * 9) * 0.25); },
      done() { paperPlane.visible = false; st.live = false; cableMat.emissiveIntensity = 0; burst(boxTop, 8); tw({ dur: 0.5, ease: EASE.out, update(e2) { CH.box.body.scale.set(1 + Math.sin(Math.PI * e2) * 0.12, 1 - Math.sin(Math.PI * e2) * 0.1, 1); CH.box.papers.rotation.z = Math.sin(e2 * 12) * 0.2; } }); } });
  }

  // ---------- money actions ----------
  function depositFx() {
    st.watching = false; const wheel = vault.refs.wheel, door = vault.refs.door; let w0;
    tw({ dur: 1.0, ease: EASE.inOut, start() { w0 = wheel.rotation.z; }, update(e) { wheel.rotation.z = w0 + e * Math.PI * 4; } });
    tw({ dur: 1.0, delay: 0.9, ease: EASE.inOut, update(e) { door.rotation.y = -1.75 * e; }, done() { shake(0.06); } });
    const c0 = O.clone().add(new V3(0.3, 1.4, -1.6)), c1 = bank.position.clone();
    tw({ dur: 0.9, delay: 1.7, ease: EASE.inOut, start() { coin.visible = true; coin.position.copy(c0); }, update(e, k) { coin.position.lerpVectors(c0, c1, e); coin.position.y += Math.sin(Math.PI * k) * 0.8; coin.rotation.y = k * 8; }, done() { coin.visible = false; burst(c1, 10, '#D9B867'); } });
    tw({ dur: 0.8, delay: 2.5, ease: EASE.inOut, update(e) { bank.rotation.y = Math.PI * e; bank.position.z = O.z + 0.95 + Math.sin(Math.PI * e) * 0.5; } });
    tw({ dur: 1.5, delay: 2.75, ease: EASE.out, update(e) { redraw(bankBackTex, bankBackDraw(Math.round(curCase().total * e), false, curCase().employer)); } });
    [2.8, 3.45].forEach(d => tw({ dur: 0.55, delay: d, ease: EASE.lin, update(e, k) { CH.frog.body.position.y = Math.sin(Math.PI * k) * 0.75; CH.frog.body.rotation.z = Math.sin(Math.PI * k) * 0.2; } }));
  }
  function matchFx() { redraw(bankBackTex, bankBackDraw(curCase().total, true, curCase().employer)); burst(bank.position.clone(), 10, '#2F5D50'); }
  function closeFx() {
    const wheel = vault.refs.wheel, door = vault.refs.door; let d0, w0;
    tw({ dur: 0.9, ease: EASE.inOut, start() { d0 = door.rotation.y; }, update(e) { door.rotation.y = d0 * (1 - e); }, done() { shake(0.08); } });
    tw({ dur: 0.8, delay: 0.85, ease: EASE.inOut, start() { w0 = wheel.rotation.z; }, update(e) { wheel.rotation.z = w0 - e * Math.PI * 2; } });
    const im = addDyn(imprintMesh('CASE CLOSED', '#2F5D50', 2.0)); im.rotation.set(-Math.PI / 2, 0, 0.08); im.position.copy(O).add(new V3(1.45, 0.03, 2.6));
    stampAt(im.position.clone(), im, 0.95, '#2F5D50', 1.5);
  }

  // ---------- flow ----------
  function resetFolderStates() {
    Object.values(folders).forEach(f => {
      if (f.imprint) { removeObj(f.imprint); f.imprint = null; }
      redraw(f.coverTex, coverDraw(CASES[f.caseId], null));
      f.pages.forEach((p, i) => { redraw(p.backTex, pageBackDraw(i, null, null)); });
    });
  }
  function goTitle(instant) {
    finishAll(); resetDynamic(); setSpeaker(null); st.camMode = 'title'; resetFolderStates();
    Object.values(folders).forEach(f => {
      const to = new V3(...titleF(f.caseId));
      if (instant) { f.pages.forEach(p => { p.t = 0; updatePage(p); }); setOpen(f, 0); f.group.position.copy(to); f.group.scale.setScalar(titleScale()); }
      else {
        f.pages.forEach((p, i) => { if (p.t > 0) turnPage(f, i, 0, 0, 0.6); });
        let o0; tw({ dur: 0.8, ease: EASE.inOut, start() { o0 = f.open; }, update(e) { setOpen(f, o0 * (1 - e)); } });
        moveTo(f.group, to, { dur: 1.1, delay: 0.5, scale: titleScale(), ease: EASE.inOut });
      }
    });
    placeChars('title', null, instant ? 0 : 0.3, instant);
  }
  function startCase(s) {
    finishAll(); resetDynamic(); resetFolderStates();
    Object.values(folders).forEach(f => { f.pages.forEach(p => { p.t = 0; updatePage(p); }); setOpen(f, 0); });
    const fid = s.caseId === 'nadia' ? 'nadia' : 'priya';
    const f = folders[fid], other = folders[fid === 'priya' ? 'nadia' : 'priya']; st.sel = f; st.caseId = s.caseId;
    f.pages.forEach((p, i) => redraw(p.frontTex, pageFrontDraw(s.case, i)));
    redraw(f.coverTex, coverDraw(s.case, null));
    st.camMode = 'zoom';
    moveTo(other.group, new V3(fid === 'priya' ? 22 : -26, 0, -4), { dur: 1.2, ease: EASE.inOut });
    moveTo(f.group, new V3(0, 0, 0), { dur: 1.2, scale: 1, ease: EASE.inOut });
    tw({ dur: 1.4, delay: 1.0, ease: EASE.inOut, update(e) { setOpen(f, e); }, done() { st.camMode = 'game'; } });
  }
  function enterRound(s, first) {
    st.roundId = s.roundId; st.ri = s.ri; st.live = false; st.stall = false; st.watching = false; st.approvals = 0; st.approvalCard = null;
    const cs = curCase(); redraw(letterTex, letterDraw(cs)); redraw(hoursTex, hoursDraw(cs)); redraw(bankFrontTex, bankFrontDraw(cs)); redraw(bankBackTex, bankBackDraw(0, false, cs.employer));
    if (first) { popUp(DIOS[s.ri], 2.1); placeChars('game', s.roundId, 2.6); }
    else {
      st.camMode = 'game'; popDown(DIOS[s.ri - 1], 0);
      clearFan(true); st.objCards = {}; st.held = {}; dyn.slice().forEach((o, k) => fadeAway(o, Math.min(0.4, k * 0.01))); dyn = [];
      if (s.ri - 1 === 1) { cable.visible = false; plug.visible = false; cableMat.emissiveIntensity = 0; }
      turnPage(st.sel, s.ri - 1, 1, 0.45, 1.6);
      popUp(DIOS[s.ri], 1.9); placeChars('game', s.roundId, 2.3);
    }
    if (s.roundId === 'money') { bank.visible = true; bank.scale.setScalar(0.001); tw({ dur: 0.6, delay: first ? 2.6 : 2.4, ease: EASE.back, update(e) { bank.scale.setScalar(Math.max(0.001, e)); } }); }
  }
  function onBeat(s) {
    const b = s.beat; if (!b) return;
    setSpeaker(b.who);
    if (st.fan && Object.keys(st.fan).length && !(b.choice)) clearFan(true);
    if (s.roundId === 'hearing') {
      if (b.card && b.card.kind === 'draft' && !b.card.shred) holdDraft();
      if (b.fx === 'shred') shredFx();
      if (b.fx === 'verify') verifyFx();
      if (b.obj && b.obj.s === 'raised') foxThrow(b.obj.n, OBJ[b.obj.n - 1]);
      if (b.obj && (b.obj.s === 'overruled' || b.obj.s === 'sustained')) { slam(0.1); stampCard(b.obj.n, b.obj.s); }
      if (b.fx === 'stamp') { slam(0.1); verdictStamp(b.stamp); }
    } else if (s.roundId === 'call') {
      if (b.fx === 'ring') plugCable();
      if (b.fx === 'stall') st.stall = true;
      if (b.card && b.card.kind === 'letter' && b.fx !== 'block') showLetter();
      if (b.fx === 'block') blockFx();
      if (b.fx === 'send') sendFx();
    } else if (s.roundId === 'money') {
      if (b.fx === 'watch') st.watching = true;
      if (b.fx === 'deposit') depositFx();
      if (b.fx === 'close') closeFx();
    }
    if (b.choice && b.choice.approval) { approvalFx(s, s.mode === 'watch' || !!s.pickedId); }
    else if (b.choice) { if (s.mode === 'watch' || s.pickedId) resolveChoice(s, s.pickedId); else showFan(s); }
  }
  function roundDoneFx(s) {
    setSpeaker(null); st.camMode = 'overview';
    const f = st.sel; if (f) redraw(f.pages[s.ri].backTex, pageBackDraw(s.ri, s.summary, s.ri === 0 ? s.verdict : null));
  }
  function finishCase(s) {
    const f = st.sel || folders[s.caseId === 'nadia' ? 'nadia' : 'priya']; st.sel = f; setSpeaker(null); st.camMode = 'results';
    DIOS.forEach(d => { if (d.pieces.some(h => h.visible)) popDown(d, 0); });
    tw({ dur: 0.4, ease: EASE.in, update(e) { [bank, letter].forEach(o => { if (o.visible) o.scale.setScalar(Math.max(0.001, 1 - e)); }); }, done() { bank.visible = false; letter.visible = false; cable.visible = false; plug.visible = false; } });
    dyn.slice().forEach(o => fadeAway(o, 0.2));
    f.pages.forEach((p, i) => { if (p.t > 0) turnPage(f, i, 0, 0.5, 0.9); });
    tw({ dur: 1.4, delay: 1.0, ease: EASE.inOut, update(e) { setOpen(f, 1 - e); }, done() { shake(0.1); } });
    placeChars('results', null, 0.4);
    const won = s.verdict === 'UPHELD', col = won ? '#2F5D50' : '#B5503E';
    if (!won) redraw(f.coverTex, coverDraw(s.case, 'No claim: withholding is correct.'));
    const im = imprintMesh(s.verdict, col, 3.3); im.position.set(-3.1, -0.006, won ? 1.8 : 2.4); im.rotation.set(Math.PI / 2, 0, Math.PI - 0.1); f.pivot.add(im); f.imprint = im;
    stampAt(new V3(3.1, 0.15, won ? 1.8 : 2.4), im, 1.45, col, 2.55);
  }

  // ---------- sync from React ----------
  let last = null;
  function sync(s) {
    const p = last; last = s; if (s.case) st.case = s.case;
    try {
      if (!p || p.runId !== s.runId || p.phase !== s.phase) {
        if (s.phase === 'title') { st.phase = 'title'; goTitle(!p); return; }
        if (s.phase === 'play') { finishAll(); st.phase = 'play'; startCase(s); enterRound(s, true); onBeat(s); return; }
        if (s.phase === 'results') { finishAll(); st.phase = 'results'; finishCase(s); return; }
        return;
      }
      if (s.phase !== 'play') return;
      if (p.ri !== s.ri) { finishAll(); enterRound(s, false); onBeat(s); return; }
      if (s.roundDone && !p.roundDone) { finishAll(); roundDoneFx(s); return; }
      if (p.bi !== s.bi) { finishAll(); if (st.camMode === 'overview') st.camMode = 'game'; onBeat(s); return; }
      if ((s.wrongIds || []).length > (p.wrongIds || []).length) wrongPick(s, s.wrongIds[s.wrongIds.length - 1]);
      if (s.pickedId && !p.pickedId) resolveChoice(s, s.pickedId);
    } catch (e) { console.warn('[docket 3d]', e); }
  }

  // ---------- picking folders on the title desk ----------
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2(); let downAt = null;
  function pick(ev) {
    const r = renderer.domElement.getBoundingClientRect(); ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera); const hit = ray.intersectObjects(folderHits, false)[0]; return hit ? hit.object.userData.caseId : null;
  }
  function onMove(ev) { if (st.phase !== 'title') { renderer.domElement.style.cursor = ''; return; } const id = pick(ev); st.hover3d = id; renderer.domElement.style.cursor = id ? 'pointer' : ''; }
  function onDown(ev) { downAt = [ev.clientX, ev.clientY]; }
  function onUp(ev) { if (!downAt || st.phase !== 'title') return; const dx = ev.clientX - downAt[0], dy = ev.clientY - downAt[1]; downAt = null; if (dx * dx + dy * dy > 64) return; const id = pick(ev); if (id && hooks.onFolderClick) hooks.onFolderClick(id); }
  function onLeave() { st.hover3d = null; }
  renderer.domElement.addEventListener('pointermove', onMove);
  renderer.domElement.addEventListener('pointerdown', onDown);
  renderer.domElement.addEventListener('pointerup', onUp);
  renderer.domElement.addEventListener('pointerleave', onLeave);

  // ---------- size / camera ----------
  let lastNarrow = null;
  function applyView() { const shift = Math.min(vh * 0.3, st.inset * 0.42); camera.aspect = vw / vh; camera.setViewOffset(vw, vh, 0, shift, vw, vh); camera.updateProjectionMatrix(); }
  function resize() { const r = mount.getBoundingClientRect(); vw = Math.max(1, Math.round(r.width)); vh = Math.max(1, Math.round(r.height)); renderer.setSize(vw, vh, false); applyView();
    const n = isNarrow(); if (lastNarrow !== null && n !== lastNarrow && st.phase === 'title') { Object.values(folders).forEach(f => { f.group.position.set(...titleF(f.caseId)); f.group.scale.setScalar(titleScale()); }); placeChars('title', null, 0, true); } lastNarrow = n; }
  let roRaf = 0; const ro = new ResizeObserver(() => { cancelAnimationFrame(roRaf); roRaf = requestAnimationFrame(resize); }); ro.observe(mount); resize();
  const cam = { pos: new V3(0, 10, 13), look: new V3(0, 0.4, 0.6) };
  const tmpLook = new V3(), tmpOff = new V3();
  function camTargets(t) {
    const a = vw / vh;
    if (st.camMode === 'title') { if (a < 1) { const f = Math.min(2.3, Math.max(1, 1.02 / a)); tmpLook.set(0, 0.4, 0.5); tmpOff.set(0, 7.0, 10.2).multiplyScalar(f); } else { const f = a < 1.6 ? Math.min(2.7, 1.6 / a) : 1; tmpLook.set(0, 0.4, 0.7); tmpOff.set(0, 8.4, 12).multiplyScalar(f); } }
    else if (st.camMode === 'zoom') { const f = a < 1.3 ? Math.min(2.3, 1.3 / a) : 1; tmpLook.set(PW / 2, 0.2, 0.2); tmpOff.set(0, 5.2, 5.0).multiplyScalar(f); }
    else if (st.camMode === 'results') { const f = a < 1.3 ? Math.min(2.4, 1.3 / a) : 1; tmpLook.set(PW / 2, 0.3, 1.2); tmpOff.set(0, 7.6, 8.4).multiplyScalar(f); }
    else if (st.camMode === 'overview') { const f = a < 1.35 ? Math.min(2.4, 1.35 / a) : 1; tmpLook.set(1.4, 0.6, 0.2); tmpOff.set(0, 7.4, 9.0).multiplyScalar(f); }
    else {
      const f = a < 1.35 ? Math.min(2.4, 1.35 / a) : 1; tmpLook.copy(O).add(new V3(0, 0.85, 0.15)); tmpOff.set(0, 5.4, 7.0).multiplyScalar(f);
      let focus = null;
      if (st.speaker && CH[st.speaker]) focus = CH[st.speaker].root.position.clone().add(new V3(0, 0.8, 0));
      else if (st.speaker === 'code') focus = O.clone().add(court.refs.shredderPos).add(new V3(0, 0.8, 0.4));
      else if (st.speaker === 'priya' && st.approvalCard) focus = st.approvalCard.position.clone().add(new V3(0, 0.4, 0));
      if (focus) { tmpLook.lerp(focus, 0.3); tmpOff.multiplyScalar(0.9); }
    }
    if (!reduce) { tmpLook.x += Math.sin(t * 0.21) * 0.3; tmpLook.y += Math.sin(t * 0.17) * 0.12; tmpOff.x += Math.sin(t * 0.13) * 0.6; tmpOff.y += Math.cos(t * 0.11) * 0.25; }
  }

  // ---------- frame loop ----------
  let lastT = performance.now(), visible = true;
  const vis = () => { visible = !document.hidden; }; document.addEventListener('visibilitychange', vis);
  const prj = new V3();
  function frame() {
    const now = performance.now(); const dt = Math.min(0.05, (now - lastT) / 1000); lastT = now; const t = now / 1000;
    if (!visible) return;
    tickTweens(now);
    // characters
    CHAR_ORDER.forEach(k => {
      const c = CH[k];
      const toCam = cam.pos.clone().sub(c.root.position); const camYaw = Math.atan2(-toCam.z, toCam.x);
      let target = c.yawBase;
      if (c.speaking || st.phase === 'title') { let d = camYaw - c.yawBase; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2; target = c.yawBase + d * (c.speaking ? 0.6 : 0.25); }
      c.yaw = dampAngle(c.yaw, target, 4, dt); c.root.rotation.y = c.yaw;
      c.body.scale.y = (k === 'box' ? c.body.scale.y : 1 + Math.sin(t * 2.2 + c.ph) * 0.022);
      if (k !== 'frog') c.body.position.y = c.speaking ? Math.abs(Math.sin(t * 6.5)) * 0.07 : 0;
      const sh = t - c.shakeT;
      c.head.rotation.y = sh < 0.8 ? Math.sin(sh * 22) * 0.35 * (1 - sh / 0.8) : 0;
      c.head.rotation.z = c.speaking ? Math.sin(t * 3.2) * 0.12 : Math.sin(t * 0.7 + c.ph) * 0.04;
      if (t > c.nextBlink) { c.blinkT = t; c.nextBlink = t + 2.5 + Math.random() * 3; }
      const bl = (t - c.blinkT) < 0.13 ? 0.12 : 1; c.eyes.forEach(e => { e.scale.y = bl; });
      if (k === 'crane') c.wings.forEach((w, i) => { const base = 0.5 + (c.speaking ? Math.sin(t * 8) * 0.3 : Math.sin(t * 1.4 + c.ph) * 0.05); w.rotation.x = damp(w.rotation.x, (i ? -1 : 1) * base, 10, dt); });
      if (k === 'fox') c.tail.rotation.y = Math.sin(t * (c.speaking ? 4 : 1.5)) * 0.35;
      if (k === 'frog') c.pupils.forEach(p => { p.position.x = 0.16; p.position.y = 0.04 + (st.watching ? Math.sin(t * 3) * 0.02 : 0); });
    });
    // hovering cards
    if ((Math.floor(t * 2) % 10) === 0 && dyn.length > 40) dyn = dyn.filter(o => o.parent);
    dyn.forEach(o => { if (o.userData.hover && o.userData.hoverBase) { o.position.y = o.userData.hoverBase.y + Math.sin(t * 2.4 + o.id) * 0.06; o.rotation.y = Math.sin(t * 1.3 + o.id) * 0.12; } });
    // folders hover lift (title)
    Object.values(folders).forEach(f => {
      const want = st.phase === 'title' && (st.hover === f.caseId || st.hover3d === f.caseId) ? 1 : 0;
      f.hoverT = damp(f.hoverT, want, 7, dt);
      if (st.phase === 'title') { f.group.position.y = f.hoverT * 0.5; f.group.rotation.x = -f.hoverT * 0.06; }
      else { f.group.position.y = damp(f.group.position.y, 0, 6, dt); f.group.rotation.x = damp(f.group.rotation.x, 0, 6, dt); }
    });
    // call props
    if (st.live || st.stall) {
      cableMat.emissiveIntensity = 0.55 + Math.sin(t * 6) * 0.35;
      lampMat.emissive.set(st.stall ? '#C0533F' : '#F2C14E'); lampMat.emissiveIntensity = (Math.sin(t * 10) > 0 ? 1 : 0.15);
      if (t - st.ringT > 0.6 && (st.speaker === 'box' || st.speaker === 'crane') && st.roundId === 'call') { st.ringT = t; ringPulse(st.stall ? '#C0533F' : '#2F5D50'); }
    } else { lampMat.emissiveIntensity = 0; }
    if (st.watching) vault.refs.wheel.rotation.z += dt * 0.8;
    if (st.shredding) court.refs.shredder.position.x = Math.sin(t * 90) * 0.015; else court.refs.shredder.position.x = 0;
    if (bank.visible && !tweens.length) bank.position.y = O.y + 1.6 + Math.sin(t * 1.6) * 0.05;
    // dust
    if (dust) { const p = dust.geometry.attributes.position; for (let i = 0; i < p.count; i++) { let y = p.getY(i) + dt * 0.05; if (y > 5.3) y = 0.3; p.setY(i, y); p.setX(i, p.getX(i) + Math.sin(t * 0.5 + i) * dt * 0.03); } p.needsUpdate = true; }
    // camera
    camTargets(t);
    const wantPos = tmpLook.clone().add(tmpOff);
    const kk = st.camMode === 'zoom' ? 2.2 : 2.6;
    cam.pos.x = damp(cam.pos.x, wantPos.x, kk, dt); cam.pos.y = damp(cam.pos.y, wantPos.y, kk, dt); cam.pos.z = damp(cam.pos.z, wantPos.z, kk, dt);
    cam.look.x = damp(cam.look.x, tmpLook.x, kk + 0.6, dt); cam.look.y = damp(cam.look.y, tmpLook.y, kk + 0.6, dt); cam.look.z = damp(cam.look.z, tmpLook.z, kk + 0.6, dt);
    camera.position.copy(cam.pos);
    if (shakeAmt > 0.001) { camera.position.x += (Math.random() - 0.5) * shakeAmt; camera.position.y += (Math.random() - 0.5) * shakeAmt; shakeAmt *= Math.exp(-dt * 8); }
    camera.lookAt(cam.look);
    renderer.render(scene, camera);
    // labels
    const els = st.labelEls;
    if (els) CHAR_ORDER.forEach(k => {
      const el = els[k]; if (!el) return; const c = CH[k];
      const show = st.phase === 'title' || st.phase === 'results' || (st.phase === 'play' && c.inRound);
      prj.copy(c.root.position); prj.y += c.top * c.root.scale.y + 0.25; prj.project(camera);
      const x = (prj.x + 1) / 2 * vw, y = (1 - prj.y) / 2 * vh - (vw < 640 && st.phase === 'title' && CHAR_ORDER.indexOf(k) % 2 ? 24 : 0);
      const onScreen = prj.z < 1 && x > -40 && x < vw + 40 && y > 30 && y < vh;
      el.style.transform = 'translate3d(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px,0) translate(-50%,-100%)';
      el.style.opacity = show && onScreen ? '1' : '0';
      el.classList.toggle('on', !!c.speaking);
    });
  }
  const rings = [];
  function ringPulse(color) {
    const r = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.025, 4, 16), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8 }));
    r.rotation.x = Math.PI / 2; r.position.copy(CH.box.root.position).add(new V3(0, 1.3, 0)); scene.add(r);
    tw({ dur: 1.2, ease: EASE.out, update(e) { r.scale.setScalar(1 + e * 2.2); r.material.opacity = 0.8 * (1 - e); }, done() { scene.remove(r); r.geometry.dispose(); r.material.dispose(); } });
  }
  renderer.setAnimationLoop(frame);
  goTitle(true);
  return {
    sync,
    hover(id) { st.hover = id; },
    setInset(px) { st.inset = px || 0; applyView(); },
    setLabelEls(m) { st.labelEls = m; },
    renderOnce() { frame(); },
    debug() { return { tweens: tweens.length, dyn: dyn.length, phase: st.phase, cam: st.camMode, round: st.roundId, info: renderer.info.render }; },
    dispose() {
      renderer.setAnimationLoop(null); ro.disconnect(); document.removeEventListener('visibilitychange', vis);
      ['pointermove', 'pointerdown', 'pointerup', 'pointerleave'].forEach((n, i) => renderer.domElement.removeEventListener(n, [onMove, onDown, onUp, onLeave][i]));
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => { if (m.map) m.map.dispose(); m.dispose(); }); });
      renderer.dispose(); if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
    },
  };
}

const CSS = `
.dc-root{container-type:inline-size;font-family:${SANS};color:${K.ink};-webkit-font-smoothing:antialiased}
.dc-root *{box-sizing:border-box}
.dc-display{font-family:${DISPLAY};font-optical-sizing:auto}
.dc-mono{font-family:${MONO}}
.dc-label{font-family:${MONO};font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:500;color:${K.faint}}
.dc-btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;min-height:48px;padding:0 22px;background:${K.ink};color:${K.card};border:0;border-radius:999px;font-family:${SANS};font-size:17px;font-weight:600;cursor:pointer;transition:transform .15s, background .2s;box-shadow:0 10px 20px -14px rgba(42,37,32,.9)}
.dc-btn:hover{background:#000}
.dc-btn:active{transform:translateY(1px)}
.dc-ghost{display:inline-flex;align-items:center;gap:8px;min-height:40px;padding:0 15px;background:rgba(251,247,239,.92);color:${K.ink};border:1px solid rgba(42,37,32,.24);border-radius:999px;font-family:${SANS};font-size:15px;font-weight:600;cursor:pointer}
.dc-ghost:hover{border-color:${K.ink}}
.dc-ghost:disabled{opacity:.45;cursor:default}
.dc-root button:focus-visible,.dc-root a:focus-visible,.dc-root summary:focus-visible{outline:2px solid ${K.green};outline-offset:3px}
.dc-sheet{position:relative;background:${K.card};border-radius:6px;box-shadow:${K.shadow}}
.dc-in{animation:dc-in .5s cubic-bezier(.2,.7,.2,1) both}
@keyframes dc-in{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.dc-fly{perspective:900px}
.dc-flip{animation:dc-flyflip .85s cubic-bezier(.2,.75,.25,1) both;transform-style:preserve-3d}
@keyframes dc-flyflip{0%{opacity:0;transform:translate3d(-26%,30px,0) rotate(-9deg) rotateY(160deg)}45%{opacity:1}100%{opacity:1;transform:none}}
.dc-stamp{display:inline-block;font-family:${MONO};font-weight:600;letter-spacing:.14em;border:3px solid currentColor;padding:6px 14px;border-radius:4px;transform:rotate(-8deg);animation:dc-stamp .6s cubic-bezier(.3,1.4,.5,1) both;background:rgba(251,247,239,.86);white-space:nowrap}
@keyframes dc-stamp{0%{opacity:0;transform:scale(2.3) rotate(-15deg)}70%{opacity:1;transform:scale(.94) rotate(-7deg)}100%{transform:scale(1) rotate(-8deg)}}
.dc-strip{animation:dc-strip 1.1s cubic-bezier(.5,0,.75,0) both}
@keyframes dc-strip{0%{transform:none}100%{transform:translateY(240px) rotate(var(--r));opacity:.2}}
.dc-shake{animation:dc-shake .45s both}
@keyframes dc-shake{0%,100%{transform:none}20%{transform:translateX(-7px) rotate(-1.5deg)}40%{transform:translateX(6px) rotate(1deg)}60%{transform:translateX(-4px)}80%{transform:translateX(3px)}}
.dc-redact{transform-origin:left center;animation:dc-redact .7s .5s cubic-bezier(.3,.7,.2,1) both}
@keyframes dc-redact{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.dc-pick{transition:transform .2s, box-shadow .2s}
.dc-pick:not(:disabled):hover{transform:translateY(-4px) rotate(-.6deg);box-shadow:0 1px 0 rgba(60,40,20,.06),0 22px 34px -18px rgba(60,40,20,.55)}
.dc-root details>summary{list-style:none;cursor:pointer}
.dc-root details>summary::-webkit-details-marker{display:none}
.dc-root details[open] .dc-chev{transform:rotate(90deg)}
.dc-chev{display:inline-block;transition:transform .2s}
.dc3-chip{background:rgba(251,247,239,.94);border-radius:999px;box-shadow:0 8px 20px -12px rgba(30,18,8,.7);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
.dc3-label{position:absolute;left:0;top:0;display:flex;flex-direction:column;align-items:center;white-space:nowrap;transition:opacity .35s;will-change:transform;pointer-events:none}
.dc3-label .n{font-family:${SANS};font-weight:700;font-size:13px;padding:3px 10px;border-radius:999px;background:rgba(251,247,239,.95);color:${K.ink};box-shadow:0 4px 10px -6px rgba(30,18,8,.7);transition:background .25s,color .25s}
.dc3-label.on .n{background:${K.ink};color:${K.card}}
.dc3-label .d{margin-top:3px;font-family:${SANS};font-weight:600;font-size:12.5px;color:#FBF7EF;text-shadow:0 1px 3px rgba(20,10,0,.85)}
.dc3-panel{position:absolute;left:50%;transform:translateX(-50%);bottom:10px;width:min(800px, calc(100% - 20px));max-height:min(58%, calc(100% - 150px));overflow-y:auto;overscroll-behavior:contain;border-radius:12px;background:rgba(251,247,239,.97);box-shadow:0 24px 50px -24px rgba(20,10,0,.75), 0 0 0 1px rgba(42,37,32,.08);z-index:5}
@container (max-width:640px){.dc3-label .d{display:none}.dc3-label .r{display:none}.dc3-label .n{font-size:12px;padding:2px 8px}.dc3-panel{max-height:min(60%, calc(100% - 170px))}}
@media (prefers-reduced-motion: reduce){.dc-root *{animation-duration:.01ms!important;animation-iteration-count:1!important}}
`;
function Stamp({ text, color, size }) {
  return <span className="dc-stamp" style={{ color, fontSize: size || 'clamp(16px, 3.4cqi, 26px)' }}>{text}</span>;
}

function Avatar({ who, size }) {
  const c = CAST[who];
  return <div className="shrink-0" style={{ width: size || 54, height: size || 54, borderRadius: 999, background: K.wall, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: who === 'code' ? 8 : 6, boxShadow: 'inset 0 0 0 1px rgba(42,37,32,.08)' }}><div style={{ width: '100%' }}><c.Art /></div></div>;
}

function Paper({ children, label, labelColor, style }) {
  return (
    <div style={Object.assign({ background: '#FFFDF8', border: '1px solid ' + K.rule, borderRadius: 4, padding: 'clamp(16px, 3.6cqi, 22px)', boxShadow: '0 12px 22px -16px rgba(60,40,20,.45)', position: 'relative' }, style)}>
      {label ? <div className="dc-label" style={{ color: labelColor || K.faint }}>{label}</div> : null}
      {children}
    </div>
  );
}

function DraftFace() {
  return (
    <Paper label="Draft quote · written by Docket’s AI" labelColor={K.red}>
      <div className="dc-display" style={{ fontSize: 'clamp(19px, 3.6cqi, 22px)', lineHeight: 1.4, marginTop: 10, fontStyle: 'italic' }}>“{DRAFT}”</div>
      <div style={{ fontSize: 16, color: K.muted, marginTop: 8 }}>Cites: IRS Publication 519</div>
    </Paper>
  );
}

function Plain({ who, text }) {
  if (!text) return null;
  return (
    <div style={{ marginTop: 14, padding: '12px 14px', borderRadius: 6, background: 'rgba(47,93,80,0.08)', boxShadow: 'inset 3px 0 0 ' + K.green }}>
      <div className="dc-label" style={{ color: K.green }}>In plain words · what this means for {who}</div>
      <div style={{ fontSize: 16.5, lineHeight: 1.55, color: K.ink, marginTop: 6 }}>{text}</div>
    </div>
  );
}
function Sources({ list }) {
  if (!list || !list.length) return null;
  return (
    <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid ' + K.rule }}>
      <div className="dc-label">Read the exact paragraph</div>
      {list.map((s, i) => <a key={i} href={s.url} target="_blank" rel="noreferrer" className="block" style={{ fontSize: 15.5, color: K.ink, textUnderlineOffset: 4, marginTop: 6, lineHeight: 1.4 }}>{s.label} ↗</a>)}
    </div>
  );
}
function irsLine(irs) {
  if (irs && irs.status === 'live') return '✓ Found word for word on the live IRS.gov page, fetched ' + irs.time;
  if (irs && irs.status === 'loading') return 'Checking the live IRS.gov page…';
  return '✓ Matched word for word (copy verified Oct 24, 2026; live IRS.gov unreachable just now)';
}
function LetterLines({ c, redacted, showRemoved }) {
  return (
    <div style={{ fontSize: 16, lineHeight: 1.6, marginTop: 10 }}>
      <div><b>To:</b> {c.employer || 'the employer'} payroll</div>
      <div><b>Re:</b> Social Security and Medicare withheld in error</div>
      <div style={{ borderTop: '1px solid ' + K.rule, margin: '10px 0' }} />
      <div>Withheld{c.stubs ? ' across ' + c.stubs + ' paystubs' : ''}: {money(c.ss)} Social Security + {money(c.med)} Medicare = <b>{money(c.total)}</b></div>
      <div>Basis: IRS Publication 519, quoted word for word</div>
      <div style={{ margin: '4px 0', padding: redacted ? '6px 8px' : 0, borderRadius: 4, background: redacted ? 'rgba(181,80,62,0.08)' : 'transparent' }}>
        <span style={{ position: 'relative', display: 'inline-block' }}>
          <span style={{ color: redacted ? K.faint : K.ink, textDecoration: redacted ? 'line-through' : 'none', textDecorationColor: K.red, textDecorationThickness: 2 }}>{c.hoursLine}</span>
        </span>
        {redacted ? <span className="dc-mono" style={{ fontSize: 13, color: K.red, fontWeight: 600, marginLeft: 10 }}>REMOVED BY GUARDIAN · not sent</span> : null}
      </div>
      <div>Sent by Docket, an AI agent, with {c.first}’s permission</div>
      {showRemoved ? <div style={{ marginTop: 10, fontSize: 15, color: K.muted }}>Removed before sending: “{c.hoursLine}”. Work hours aren’t needed for a refund request.</div> : null}
    </div>
  );
}

function CardView({ card, flags, k }) {
  const c = card.c || CASES.priya, who = c.first;
  let body = null;
  if (card.kind === 'draft') body = (
    <Paper label="Draft quote · written by Docket’s AI" labelColor={K.red}>
      <div className="dc-display" style={{ fontSize: 'clamp(19px, 3.6cqi, 22px)', lineHeight: 1.4, marginTop: 10, fontStyle: 'italic', textDecoration: card.shred ? 'line-through' : 'none', textDecorationColor: K.red, color: card.shred ? K.faint : K.ink }}>“{DRAFT}”</div>
      <div style={{ fontSize: 16, color: K.muted, marginTop: 8 }}>Cites: IRS Publication 519</div>
      {card.shred ? (
        <div className="flex items-center gap-3 flex-wrap" style={{ marginTop: 12 }}>
          <Stamp text="REJECTED" color={K.red} size="16px" />
          <span style={{ fontSize: 15.5, color: K.red, fontWeight: 600 }}>{card.irs && card.irs.status === 'live' ? '✕ Not on the live IRS.gov page (fetched ' + card.irs.time + ')' : '✕ Not in IRS Publication 519'}</span>
        </div>
      ) : null}
    </Paper>
  );
  if (card.kind === 'quote') body = (
    <Paper label="Official source · IRS.gov" labelColor={K.ink}>
      <div className="dc-display" style={{ fontSize: 'clamp(19px, 3.6cqi, 22px)', lineHeight: 1.42, marginTop: 10 }}>“{P519.quote}”</div>
      <div className="flex items-end justify-between gap-3 flex-wrap" style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid ' + K.rule }}>
        <div style={{ fontSize: 15, lineHeight: 1.45 }}><div style={{ fontWeight: 600 }}>{P519.title}</div><div style={{ color: K.muted }}>{P519.section}</div></div>
        <a href={P519.url} target="_blank" rel="noreferrer" style={{ fontSize: 15, color: K.ink, textUnderlineOffset: 4 }}>Open this exact sentence ↗</a>
      </div>
      <div style={{ fontSize: 15, color: K.green, fontWeight: 600, marginTop: 10 }}>{irsLine(card.irs)}</div>
      <Plain who={who} text={card.plain} />
    </Paper>
  );
  if (card.kind === 'evidence') body = (
    <Paper label="Evidence card" labelColor={K.green}>
      <div className="dc-display" style={{ fontSize: 'clamp(20px, 3.8cqi, 24px)', lineHeight: 1.2, marginTop: 8 }}>{card.title}</div>
      <ul style={{ margin: '10px 0 0', padding: 0, listStyle: 'none' }}>
        {card.lines.map((l, i) => <li key={i} className="flex gap-3" style={{ fontSize: 16.5, lineHeight: 1.5, padding: '3px 0' }}><span aria-hidden style={{ width: 7, height: 7, background: K.green, transform: 'rotate(45deg) translateY(9px)', flexShrink: 0, marginTop: 2 }} /><span>{l}</span></li>)}
      </ul>
      <Plain who={who} text={card.plain} />
      <Sources list={card.src} />
    </Paper>
  );
  if (card.kind === 'letter') body = (
    <Paper label="Written request · draft" labelColor={K.ink}>
      <LetterLines c={c} redacted={flags.redacted} />
    </Paper>
  );
  if (card.kind === 'review') body = (
    <Paper label={'Final letter · ' + who + ' reviews before sending'} labelColor={K.green}>
      <LetterLines c={c} redacted showRemoved />
      <div style={{ marginTop: 10, fontSize: 15, color: K.muted }}>Nothing leaves Docket until {who} approves this exact text.</div>
    </Paper>
  );
  if (card.kind === 'callreq') body = (
    <Paper label={'Permission request · ' + who + ' decides'} labelColor={K.green}>
      <div style={{ fontSize: 16.5, lineHeight: 1.6, marginTop: 10 }}>
        <div><b>Docket wants to:</b> call {c.employer || 'the employer'} payroll about {money(c.total)}.</div>
        <div><b>Docket will say:</b> it’s an AI calling with {who}’s permission, and the call may be recorded.</div>
        <div><b>Docket won’t:</b> pretend to be {who}, or share anything beyond the claim.</div>
        <div><b>After the call:</b> anything written gets shown to {who} before it’s sent.</div>
      </div>
    </Paper>
  );
  if (!body) return null;
  return <div className="dc-fly" key={k}><div className="dc-flip">{body}</div></div>;
}

function beatDur(b, mode) {
  if (b.choice && mode === 'argue') return 1900;
  if (b.fx === 'shred') return 7600;
  if (b.fx === 'stamp' || b.fx === 'close') return 5000;
  const t = b.choice ? b.choice.watchText : b.text;
  return Math.min(8600, Math.max(3200, 1600 + t.length * 46)) + (b.card || b.choice ? 1600 : 0);
}


function whoName(who, c) { return who === 'priya' ? c.first : CAST[who].name; }
function centsOf(s) { const n = parseFloat(String(s || '').replace(/[$,\s]/g, '')); return isFinite(n) && n > 0 ? Math.round(n * 100) : 0; }
function buildCustom(f) {
  const errs = [];
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.arrival || '')) errs.push('arrival date');
  else { const y = +f.arrival.slice(0, 4); if (y > NOW_YEAR || y < 1980) errs.push('a real arrival year'); }
  if (!(f.employer || '').trim()) errs.push('employer');
  const ss = centsOf(f.ss), med = centsOf(f.med);
  if (!ss && !med) errs.push('the amounts withheld');
  if (errs.length) return { ok: false, errs };
  const name = (f.name || '').trim() || 'Student';
  const stubs = parseInt(f.stubs, 10) > 0 ? Math.min(99, parseInt(f.stubs, 10)) : 0;
  return { ok: true, c: makeCase({ id: 'custom', custom: true, name, first: name.split(/\s+/)[0], visa: f.visa, arrival: f.arrival, employer: f.employer.trim(), stubs, ss, med }) };
}

function UserDiv() {
  const [phase, setPhase] = React.useState('title');
  const [caseId, setCaseId] = React.useState('priya');
  const [mode, setMode] = React.useState('watch');
  const [ri, setRi] = React.useState(0);
  const [bi, setBi] = React.useState(0);
  const [roundDone, setRoundDone] = React.useState(false);
  const [playing, setPlaying] = React.useState(true);
  const [res, setRes] = React.useState({});
  const [fb, setFb] = React.useState(null);
  const [runId, setRunId] = React.useState(0);
  const [ready, setReady] = React.useState(false);
  const [err3d, setErr3d] = React.useState(null);
  const mountRef = React.useRef(null), worldRef = React.useRef(null), panelRef = React.useRef(null), rootRef = React.useRef(null);
  const labelRefs = React.useRef({});
  const modeRef = React.useRef(mode); modeRef.current = mode;
  const phaseRef = React.useRef(phase); phaseRef.current = phase;
  const startRef = React.useRef(null);

  const [custom, setCustom] = React.useState({ name: '', visa: 'F-1', arrival: '', employer: '', ss: '', med: '', stubs: '' });
  const [irs, setIrs] = React.useState({ status: 'loading' });
  const customCase = React.useMemo(() => buildCustom(custom), [custom]);
  const c = caseId === 'custom' ? (customCase.ok ? customCase.c : CASES.priya) : CASES[caseId];
  const irsKey = irs.status + (irs.time || '');
  const rounds = React.useMemo(() => buildRounds(c, irs), [c, irsKey]);
  const round = rounds[Math.min(ri, rounds.length - 1)];
  const beats = round.beats;
  const beat = beats[Math.min(bi, beats.length - 1)];
  const bkey = ri + '-' + bi;
  const picked = res[bkey] && res[bkey].picked;
  const wrongIds = (res[bkey] && res[bkey].wrong) || [];
  const waiting = phase === 'play' && !roundDone && mode === 'argue' && !!beat.choice && !picked;

  const start = (id, m) => {
    if (id === 'custom' && !customCase.ok) { setCaseId('custom'); return; }
    setCaseId(id); setMode(m); setRi(0); setBi(0); setRoundDone(false); setPlaying(true); setRes({}); setFb(null); setPhase('play'); setRunId(r => r + 1);
  };
  startRef.current = (id) => { if (phaseRef.current === 'title') start(id, modeRef.current); };
  const advance = () => {
    if (waiting) return;
    setFb(null);
    if (bi < beats.length - 1) setBi(bi + 1); else setRoundDone(true);
  };
  const nextRound = () => {
    setFb(null);
    if (ri < rounds.length - 1) { setRi(ri + 1); setBi(0); setRoundDone(false); }
    else setPhase('results');
  };

  React.useEffect(() => {
    if (phase !== 'play' || !playing) return;
    if (roundDone) { if (mode === 'watch') { const t = setTimeout(nextRound, 4200); return () => clearTimeout(t); } return; }
    if (waiting) return;
    const t = setTimeout(advance, beatDur(beat, mode));
    return () => clearTimeout(t);
  }, [phase, playing, roundDone, waiting, ri, bi, mode, res]);

  const pick = (o) => {
    const cur = res[bkey] || { wrong: [] };
    if (cur.picked || cur.wrong.indexOf(o.id) >= 0) return;
    if (o.correct) { setRes(Object.assign({}, res, { [bkey]: { picked: o.id, wrong: cur.wrong } })); setFb({ ok: true, text: 'Admitted.' }); }
    else { setRes(Object.assign({}, res, { [bkey]: { picked: null, wrong: cur.wrong.concat([o.id]) } })); setFb({ ok: false, text: o.feedback, id: o.id }); }
  };

  // ---- 3D world lifecycle ----
  React.useEffect(() => {
    let dead = false, world = null;
    (async () => {
      try {
        const THREE = await loadThree();
        const fontsReady = Promise.all([document.fonts.load("600 40px Fraunces"), document.fonts.load("500 30px Figtree"), document.fonts.load("700 30px Figtree"), document.fonts.load("600 30px 'IBM Plex Mono'"), document.fonts.load("700 30px 'IBM Plex Mono'")]).catch(() => null);
        await Promise.race([fontsReady, new Promise(r => setTimeout(r, 2500))]);
        if (dead || !mountRef.current) return;
        world = createWorld(THREE, mountRef.current, { onFolderClick: (id) => startRef.current && startRef.current(id) });
        world.setLabelEls(labelRefs.current);
        worldRef.current = world; window.__docket3d = world; setReady(true);
      } catch (e) { console.error('[docket 3d] could not start', e); if (!dead) setErr3d(String((e && e.message) || e)); }
    })();
    return () => { dead = true; if (world) world.dispose(); worldRef.current = null; if (window.__docket3d === world) delete window.__docket3d; };
  }, []);

  // live quote check: fetch the real IRS Publication 519 page in the browser and search it
  React.useEffect(() => {
    let dead = false; const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 15000);
    fetch(IRS_FETCH_URL, { signal: ctl.signal })
      .then(r => (r.ok ? r.text() : Promise.reject(new Error('HTTP ' + r.status))))
      .then(h => {
        const t = h.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');
        if (dead) return;
        const d = new Date();
        setIrs({ status: 'live', time: d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }), quoteFound: t.includes(P519.quote), draftFound: t.includes(DRAFT), kb: Math.round(h.length / 1024) });
      })
      .catch(e => { if (!dead) setIrs({ status: 'fallback', reason: String((e && e.message) || e) }); })
      .finally(() => clearTimeout(to));
    return () => { dead = true; ctl.abort(); clearTimeout(to); };
  }, []);

  // keep the stage clear of the dialogue card
  React.useEffect(() => {
    const el = panelRef.current; if (!el) return;
    let raf = 0; const ro = new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => { const w = worldRef.current; if (w) w.setInset(el.getBoundingClientRect().height); }); });
    ro.observe(el); return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, [ready, phase]);

  // objection in play for the current choice
  let objN = 1;
  for (let i = 0; i <= Math.min(bi, beats.length - 1); i++) if (beats[i].obj && beats[i].obj.s === 'raised') objN = beats[i].obj.n;
  const roundSummary = ri === 0 ? (c.exempt ? 'Claim upheld. All four objections overruled.' : 'Claim defeated. The year count settled it.')
    : ri === 1 ? 'Written request sent after ' + c.first + ' approved it. ' + c.first + '’s work hours stayed out of it.' : money(c.total) + ' matched to the case, to the cent. Case closed.';

  React.useEffect(() => {
    const w = worldRef.current; if (!w) return;
    w.sync({ phase, runId, caseId, case: c, mode, ri, bi, roundDone, roundId: round.meta.id, beat, objN, pickedId: picked || null, wrongIds: wrongIds.slice(), summary: roundSummary, verdict: c.verdict });
  }, [ready, phase, runId, ri, bi, roundDone, picked, wrongIds.length]);

  // derived flags for the HTML cards (unchanged)
  const flags = { verdict: null, redacted: false, deposit: false, matched: false, closed: false, playedCard: false };
  const objStatus = [null, null, null, null];
  for (let i = 0; i <= Math.min(bi, beats.length - 1); i++) {
    const b = beats[i];
    if (b.stamp && b.fx === 'stamp') flags.verdict = b.stamp;
    if (b.fx === 'block') flags.redacted = true;
    if (b.fx === 'match' && (i < bi || roundDone || mode === 'watch' || (res[ri + '-' + i] && res[ri + '-' + i].picked))) flags.matched = true;
    if (b.obj) objStatus[b.obj.n - 1] = b.obj.s;
    if (b.objRest) for (let j = 1; j < 4; j++) if (!objStatus[j]) objStatus[j] = 'not reached';
  }
  if (roundDone) beats.forEach(b => { if (b.fx === 'block') flags.redacted = true; });

  let choices = 0, firstTry = 0;
  rounds.forEach((r, i) => r.beats.forEach((b, j) => { if (b.choice && !b.choice.approval) { const x = res[i + '-' + j]; if (x && x.picked) { choices++; if (!x.wrong.length) firstTry++; } } }));
  const shown = useCountUp(phase === 'results' ? c.recovered : 0, 1500);

  const Honest = () => (
    <span className="dc-mono dc3-chip inline-flex items-center gap-2" style={{ fontSize: 13, padding: '7px 12px', border: '1.5px dashed rgba(42,37,32,.38)', color: K.ink, lineHeight: 1.3 }}>
      <span aria-hidden style={{ width: 7, height: 7, borderRadius: 9, background: K.kraftDark }} />{HONEST}
    </span>
  );
  const hoverCase = (id) => { const w = worldRef.current; if (w) w.hover(id); };

  // ---------------- panels ----------------
  let panel = null;
  const liveChip = irs.status === 'live'
    ? 'Quote checker is live: IRS Publication 519 loaded from IRS.gov at ' + irs.time + ' · real clause ' + (irs.quoteFound ? 'found' : 'NOT found') + ' · made-up draft ' + (irs.draftFound ? 'found' : 'not found')
    : irs.status === 'loading' ? 'Quote checker: loading IRS Publication 519 from IRS.gov…' : 'Quote checker: IRS.gov unreachable right now, using the copy verified Oct 24, 2026';
  if (phase === 'title') {
    const cc = customCase;
    const setF = (k, v) => setCustom(prev => Object.assign({}, prev, { [k]: v }));
    const fieldStyle = { width: '100%', height: 44, borderRadius: 8, border: '1px solid rgba(42,37,32,.22)', background: '#FFFDF8', padding: '0 12px', fontSize: 16, color: K.ink, fontFamily: SANS };
    const F = (label, el) => <label className="block min-w-0"><span className="block" style={{ fontSize: 14, fontWeight: 600, color: K.muted, marginBottom: 4 }}>{label}</span>{el}</label>;
    panel = (
      <div style={{ padding: 'clamp(16px, 3.4cqi, 26px)' }} className="flex flex-col gap-5">
        <div className="dc-in">
          <h1 className="dc-display" style={{ fontSize: 'clamp(34px, 6.5cqi, 54px)', lineHeight: 0.98, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>Docket: <span style={{ color: K.green }}>The Case</span></h1>
          <p style={{ fontSize: 17, lineHeight: 1.55, color: K.muted, margin: '10px 0 0', maxWidth: 600 }}>A 3-round game about how Docket’s agents fight for an F-1 student’s money: a hearing, a phone call, and the money landing in the bank.</p>
          <div className="flex items-start gap-2" style={{ marginTop: 12, fontSize: 15, lineHeight: 1.45, color: irs.status === 'live' ? K.green : K.muted, fontWeight: 600 }}>
            <span aria-hidden style={{ width: 8, height: 8, borderRadius: 9, marginTop: 6, flexShrink: 0, background: irs.status === 'live' ? K.green : K.kraftDark }} />{liveChip}
          </div>
        </div>
        <div className="dc-in" style={{ animationDelay: '80ms' }}>
          <div className="dc-label" style={{ marginBottom: 10 }}>1 · Pick a case <span style={{ textTransform: 'none', letterSpacing: 0, fontFamily: SANS, fontSize: 13 }}>· or click a folder on the desk</span></div>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 230px), 1fr))' }}>
            {['priya', 'nadia', 'custom'].map(id => {
              const on = caseId === id, isC = id === 'custom';
              const title = isC ? 'Your own case' : CASES[id].name;
              const facts = isC ? ['Enter any student’s facts', 'The verdict is computed by the rules, live'] : CASES[id].facts;
              return (
                <button key={id} type="button" onClick={() => setCaseId(id)} onMouseEnter={() => !isC && hoverCase(id)} onMouseLeave={() => hoverCase(null)} onFocus={() => !isC && hoverCase(id)} onBlur={() => hoverCase(null)} aria-pressed={on} className="dc-pick text-left dc-sheet"
                  style={{ padding: '14px 16px', border: 0, cursor: 'pointer', background: on ? '#FFFDF8' : K.card, boxShadow: on ? '0 0 0 2px ' + K.green + ', ' + K.shadow : K.shadow }}>
                  <span className="dc-label block" style={{ color: isC ? K.green : K.faint, marginBottom: 4 }}>{isC ? 'Live rules' : 'Story case'}</span>
                  <span className="flex items-center justify-between gap-3">
                    <span className="dc-display" style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.1 }}>{title}</span>
                    <span style={{ fontSize: 15, fontWeight: 700, color: on ? K.green : K.faint, whiteSpace: 'nowrap' }}>{on ? '✓' : ''}</span>
                  </span>
                  <span className="block" style={{ marginTop: 6 }}>{facts.map((f, i) => <span key={i} className="block" style={{ fontSize: 16, lineHeight: 1.45, color: K.muted }}>{f}</span>)}</span>
                </button>
              );
            })}
          </div>
          {caseId === 'custom' ? (
            <div className="dc-in dc-sheet" style={{ marginTop: 12, padding: 16 }}>
              <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))' }}>
                {F('Student name', <input style={fieldStyle} value={custom.name} placeholder="e.g. Alex Kim" onChange={e => setF('name', e.target.value)} />)}
                {F('Visa', <select style={fieldStyle} value={custom.visa} onChange={e => setF('visa', e.target.value)}><option value="F-1">F-1 student</option><option value="J-1">J-1 student</option><option value="M-1">M-1 student</option></select>)}
                {F('First US arrival date', <input type="date" style={fieldStyle} value={custom.arrival} max={NOW_YEAR + '-12-31'} onChange={e => setF('arrival', e.target.value)} />)}
                {F('Employer', <input style={fieldStyle} value={custom.employer} placeholder="e.g. Campus Bookstore" onChange={e => setF('employer', e.target.value)} />)}
                {F('Social Security withheld ($)', <input inputMode="decimal" style={fieldStyle} value={custom.ss} placeholder="0.00" onChange={e => setF('ss', e.target.value.replace(/[^0-9.,]/g, ''))} />)}
                {F('Medicare withheld ($)', <input inputMode="decimal" style={fieldStyle} value={custom.med} placeholder="0.00" onChange={e => setF('med', e.target.value.replace(/[^0-9.,]/g, ''))} />)}
                {F('Paystubs (optional)', <input inputMode="numeric" style={fieldStyle} value={custom.stubs} placeholder="e.g. 4" onChange={e => setF('stubs', e.target.value.replace(/[^0-9]/g, ''))} />)}
              </div>
              <div style={{ marginTop: 12, fontSize: 16, lineHeight: 1.5, color: cc.ok ? (cc.c.exempt ? K.green : K.red) : K.muted, fontWeight: 600 }}>
                {cc.ok
                  ? 'Rules in code: arrived ' + cc.c.arrivalYear + ', so ' + NOW_YEAR + ' is calendar year ' + cc.c.yearNo + (cc.c.exempt ? ' of 5. The claim for ' + money(cc.c.total) + ' should likely hold.' : ', past the 5-year window. The claim will likely fail, honestly.') + (cc.c.yearNo > 12 ? ' Check this date: it should be the day you first arrived in the US on a student visa, not your birth date.' : '')
                  : 'Still needed: ' + cc.errs.join(', ') + '.'}
              </div>
              <div style={{ marginTop: 4, fontSize: 15, color: K.muted }}>Nothing you type is saved. The phone call and the bank stay simulated.</div>
            </div>
          ) : null}
        </div>
        <div className="dc-in" style={{ animationDelay: '140ms' }}>
          <div className="dc-label" style={{ marginBottom: 10 }}>2 · Pick a mode</div>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 250px), 1fr))' }}>
            {[['watch', 'Watch the agents', 'Sit back. The agents play the case out.'], ['argue', 'Argue it yourself', 'You pick the evidence cards the crane plays, and approve or hold each action as the student.']].map(([id, t, d]) => {
              const on = mode === id;
              return (
                <button key={id} type="button" onClick={() => setMode(id)} aria-pressed={on} className="dc-sheet text-left flex items-start gap-3" style={{ padding: '13px 16px', cursor: 'pointer', border: 0, boxShadow: on ? '0 0 0 2px ' + K.ink + ', ' + K.shadow : K.shadow, background: on ? '#FFFDF8' : K.card }}>
                  <span aria-hidden style={{ width: 20, height: 20, borderRadius: 99, border: '2px solid ' + (on ? K.ink : K.faint), marginTop: 3, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{on ? <span style={{ width: 9, height: 9, borderRadius: 9, background: K.ink }} /> : null}</span>
                  <span><span className="block" style={{ fontSize: 17, fontWeight: 700 }}>{t}</span><span className="block" style={{ fontSize: 16, color: K.muted, lineHeight: 1.4, marginTop: 2 }}>{d}</span></span>
                </button>
              );
            })}
          </div>
        </div>
        <div className="dc-in flex items-center gap-4 flex-wrap" style={{ animationDelay: '200ms' }}>
          <button type="button" className="dc-btn" disabled={caseId === 'custom' && !cc.ok} style={caseId === 'custom' && !cc.ok ? { opacity: 0.45, cursor: 'default' } : null} onClick={() => start(caseId, mode)} onMouseEnter={() => caseId !== 'custom' && hoverCase(caseId)} onMouseLeave={() => hoverCase(null)}>{caseId === 'custom' ? 'Run this case →' : 'Open ' + CASES[caseId].first + '’s case →'}</button>
          <span style={{ fontSize: 16, color: K.muted }}>{caseId === 'custom' ? 'The verdict comes from the rules, not a script.' : 'About 3 minutes. Figures come from Docket’s demo data.'}</span>
        </div>
      </div>
    );
  } else if (phase === 'results') {
    const won = c.verdict === 'UPHELD', live = irs.status === 'live';
    const report = won ? [
      ['crane', 'Filed the claim, answered 4 objections with official evidence, and sent the letter ' + c.first + ' approved.'],
      ['fox', 'Raised 4 objections for the employer. All 4 overruled.'],
      ['owl', 'Counted calendar years in code: ' + NOW_YEAR + ' is year ' + c.yearNo + ' of 5. Ruled UPHELD.'],
      ['code', 'Caught 1 made-up quote before anyone saw it' + (live ? ', checked against the live IRS.gov page.' : '.')],
      ['priya', 'Approved 2 actions before Docket acted: the payroll call and the final letter.'],
      ['turtle', 'Removed “' + c.hoursLine + '” from the letter. It was never sent.'],
      ['box', 'Stalled on the phone, then received the written request.'],
      ['frog', 'Matched the ' + money(c.total) + ' deposit to the case, to the cent, and closed it.'],
    ] : [
      ['crane', 'Filed the claim, then conceded when the year count went against ' + (c.custom ? 'them' : 'her') + '.'],
      ['fox', 'Raised 1 objection, the year count. Sustained.'],
      ['owl', 'Counted in code: ' + NOW_YEAR + ' is year ' + c.yearNo + ', past the 5-year limit. Ruled DEFEATED.'],
      ['code', 'Caught 1 made-up quote before anyone saw it' + (live ? ', checked against the live IRS.gov page.' : '.')],
      ['priya', 'Nothing to approve: Docket didn’t contact anyone.'],
      ['turtle', 'Nothing was sent, so nothing to protect.'],
      ['box', 'Never contacted.'],
      ['frog', 'No refund to watch for.'],
    ];
    panel = (
      <div style={{ padding: 'clamp(18px, 3.6cqi, 28px)' }} className="flex flex-col gap-4">
        <div className="dc-in flex items-end justify-between gap-4 flex-wrap">
          <div>
            <div className="dc-label" style={{ color: won ? K.green : K.ink }}>{won ? 'Case closed' : 'Case decided'} · {c.name}{c.custom ? ' · live rules' : ''}</div>
            <div className="dc-display" aria-label={money(c.recovered)} style={{ fontSize: 'clamp(56px, 12cqi, 104px)', lineHeight: 0.95, letterSpacing: '-0.035em', color: won ? K.green : K.ink, marginTop: 10, fontVariantNumeric: 'tabular-nums lining-nums' }}>
              <span style={{ fontSize: '0.5em', verticalAlign: '0.62em', marginRight: '0.04em' }}>$</span>{money(shown).slice(1)}
            </div>
            <div style={{ fontSize: 18, marginTop: 8 }}>{won ? 'recovered for ' + c.first + ' (simulated deposit)' : 'recovered · nothing was owed'}</div>
            {!won ? <div style={{ fontSize: 18, marginTop: 4, fontWeight: 700, color: K.red }}>No claim: withholding is correct.</div> : null}
          </div>
          <Stamp text={c.verdict} color={won ? K.green : K.red} />
        </div>
        <div className="dc-in" style={{ animationDelay: '120ms' }}>
          {[
            ['Verdict', won ? 'UPHELD · all four objections overruled' : 'DEFEATED · withholding is likely correct'],
            ['Money recovered', won ? money(c.total) + ' = ' + money(c.ss) + ' Social Security + ' + money(c.med) + ' Medicare' : '$0.00'],
            ['Made-up quotes caught', '1 made-up quote caught'],
            ['Human approvals', won ? c.first + ' approved 2 actions: the payroll call and the final letter' : 'None needed: nothing was sent'],
            ['Removed for privacy', won ? '“' + c.hoursLine + '”, struck from the letter before sending' : 'Nothing was sent'],
            ['Quote check', live ? 'Live IRS.gov page, fetched at ' + irs.time : 'Saved copy verified Oct 24, 2026'],
            ['Rounds played', won ? '3 of 3' : '1 of 3 · the call and the money weren’t needed'],
          ].concat(mode === 'argue' ? [['Your evidence', firstTry + ' of ' + choices + ' cards right on the first try']] : []).map(([k2, v], i) => (
            <div key={k2} className="grid gap-1 sm:gap-6 py-2.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', borderTop: i ? '1px solid ' + K.rule : '1px solid ' + K.ink }}>
              <span style={{ fontSize: 16, color: K.muted }}>{k2}</span>
              <span style={{ fontSize: 17, fontWeight: 600, color: k2 === 'Made-up quotes caught' ? K.red : K.ink }}>{v}</span>
            </div>
          ))}
        </div>
        <div className="dc-in" style={{ animationDelay: '160ms' }}>
          <div className="dc-label" style={{ marginBottom: 8 }}>What each agent did</div>
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))' }}>
            {report.map(([w, t]) => (
              <div key={w} className="flex items-start gap-3" style={{ padding: '10px 12px', borderRadius: 8, background: 'rgba(234,223,203,.45)', boxShadow: 'inset 0 0 0 1px ' + K.rule }}>
                <Avatar who={w} size={44} />
                <div className="min-w-0">
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{whoName(w, c)} <span style={{ fontWeight: 500, color: K.muted }}>· {CAST[w].role}</span></div>
                  <div style={{ fontSize: 16, lineHeight: 1.45, color: K.ink, marginTop: 2 }}>{t}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="dc-in" style={{ fontSize: 17, lineHeight: 1.6, color: K.muted, margin: 0, animationDelay: '180ms' }}>
          {won ? 'Docket filed the claim, answered every objection with official evidence, asked ' + c.first + ' before acting, kept ' + c.her + ' private details out of the letter, and only closed the case when the deposit matched to the cent.'
            : 'Docket argued, checked the year count in code, and lost honestly. With nothing owed, it didn’t contact payroll or chase money that isn’t ' + (c.custom ? 'theirs' : 'hers') + '. If ' + c.s + ' never intended to stay permanently and kept to ' + c.her + ' visa rules, a narrow IRS exception may still apply; that is a question for the international office, not for code.'}
        </p>
        <div className="dc-in flex items-start gap-3" style={{ fontSize: 18, fontWeight: 700, animationDelay: '220ms' }}><span aria-hidden style={{ width: 20, height: 2, background: K.ink, marginTop: 13, flexShrink: 0 }} /><span>{CONFIRM}</span></div>
        <div className="dc-in flex items-center gap-3 flex-wrap" style={{ animationDelay: '260ms' }}>
          <button type="button" className="dc-btn" onClick={() => start(caseId, mode)}>Play again</button>
          <button type="button" className="dc-ghost" style={{ minHeight: 48, fontSize: 16 }} onClick={() => start(caseId === 'priya' ? 'nadia' : 'priya', mode)}>Try {caseId === 'priya' ? 'Nadia' : 'Priya'}’s case</button>
          <button type="button" className="dc-ghost" style={{ minHeight: 48, fontSize: 16 }} onClick={() => setPhase('title')}>Back to title</button>
        </div>
      </div>
    );
  } else {
    const choice = beat.choice;
    const correctOpt = choice ? choice.options.find(o => o.correct) : null;
    const pickedOpt = choice && picked ? choice.options.find(o => o.id === picked) : null;
    const showText = choice ? (mode === 'watch' || picked ? choice.watchText : choice.prompt) : beat.text;
    const isApproval = !!(choice && choice.approval);
    const rawCard = isApproval ? beat.card : choice ? (mode === 'watch' ? optCard(correctOpt) : pickedOpt ? optCard(pickedOpt) : null) : beat.card;
    const showCard = rawCard ? Object.assign({}, rawCard, { c, irs }) : null;
    const last = ri === rounds.length - 1;
    const transcript = beats.slice(0, roundDone ? beats.length : bi).map((b, i) => ({ who: b.who, text: b.choice ? b.choice.watchText : b.text, i }));
    const speaker = CAST[beat.who];
    panel = (
      <div style={{ padding: 'clamp(14px, 3.2cqi, 22px)' }} className="flex flex-col gap-3">
        {ri === 0 ? (
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))' }}>
            {OBJ.map((label, i) => {
              const s = objStatus[i];
              const col = s === 'overruled' ? K.green : s === 'sustained' ? K.red : s === 'raised' ? K.ink : K.faint;
              return (
                <div key={i} className="flex items-start gap-2" style={{ padding: '7px 10px', borderRadius: 6, background: s === 'raised' ? '#FFFDF8' : 'rgba(234,223,203,.45)', boxShadow: s === 'raised' ? '0 0 0 1.5px ' + K.ink : 'inset 0 0 0 1px ' + K.rule, transition: 'box-shadow .3s' }}>
                  <span className="dc-mono" style={{ fontSize: 14, fontWeight: 600, color: col, minWidth: 14 }}>{i + 1}</span>
                  <span className="min-w-0">
                    <span className="block" style={{ fontSize: 14.5, lineHeight: 1.3, fontWeight: 600, color: s ? K.ink : K.faint }}>{label}</span>
                    <span className="block" style={{ fontSize: 13.5, fontWeight: 600, color: col, marginTop: 1 }}>{s === 'overruled' ? '✓ Overruled' : s === 'sustained' ? 'Sustained' : s === 'raised' ? 'Raised' : s === 'not reached' ? 'Not reached' : 'Pending'}</span>
                  </span>
                </div>
              );
            })}
          </div>
        ) : null}
        {roundDone ? (
          <div key={'done' + ri} className="dc-in">
            <div className="dc-label" style={{ color: K.green }}>Round {ri + 1} complete</div>
            <div className="dc-display" style={{ fontSize: 'clamp(24px, 4.4cqi, 32px)', lineHeight: 1.2, marginTop: 6 }}>{roundSummary}</div>
            {!c.exempt ? <p style={{ fontSize: 17, lineHeight: 1.55, color: K.muted, margin: '8px 0 0' }}>Rounds 2 and 3 are skipped: nothing is owed, so Docket doesn’t call payroll or watch the bank.</p> : null}
            <div className="flex items-center gap-3 flex-wrap" style={{ marginTop: 14 }}>
              <button type="button" className="dc-btn" onClick={nextRound}>{last ? 'See the results →' : 'Next round: ' + ROUND_META[ri + 1].title + ' →'}</button>
              {mode === 'watch' && playing ? <span style={{ fontSize: 16, color: K.faint }}>Continuing automatically…</span> : null}
            </div>
          </div>
        ) : (
          <div key={bkey} className="dc-in">
            <div className="flex items-center gap-3">
              <Avatar who={beat.who} size={50} />
              <div className="min-w-0">
                <div style={{ fontSize: 17, fontWeight: 700 }}>{whoName(beat.who, c)} <span style={{ fontWeight: 500, color: K.muted }}>· {speaker.role}</span></div>
                <div style={{ fontSize: 15, color: K.faint }}>{speaker.note}</div>
              </div>
            </div>
            <p style={{ fontSize: 'clamp(17px, 2.4cqi, 19px)', lineHeight: 1.55, margin: '12px 0 0', color: K.ink }}>{showText}</p>
            {showCard ? <div style={{ marginTop: 14 }}><CardView card={showCard} flags={flags} k={bkey + (picked || '')} /></div> : null}
            {beat.banner ? (
              <div className="dc-in" style={{ marginTop: 14, padding: '13px 15px', borderRadius: 6, background: K.redSoft, boxShadow: 'inset 0 0 0 1.5px rgba(181,80,62,.45)', animationDelay: '2.3s' }}>
                <div style={{ fontSize: 17, lineHeight: 1.5, color: K.ink }}><b style={{ color: K.red }}>Made-up quote caught:</b> {beat.banner.replace('Made-up quote caught: ', '')}</div>
              </div>
            ) : null}
            {choice && mode === 'argue' && !picked ? (
              <div style={{ marginTop: 14 }}>
                <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))' }}>
                  {choice.options.map((o, i) => {
                    const wrong = wrongIds.indexOf(o.id) >= 0;
                    return (
                      <button key={o.id} type="button" disabled={wrong} onClick={() => pick(o)} className={'dc-pick dc-in text-left' + (wrong && fb && fb.id === o.id ? ' dc-shake' : '')}
                        style={{ position: 'relative', animationDelay: (i * 90) + 'ms', background: wrong ? 'rgba(251,247,239,.6)' : '#FFFDF8', border: '1px solid ' + (wrong ? K.rule : 'rgba(42,37,32,.2)'), borderRadius: 6, padding: '13px 15px', cursor: wrong ? 'default' : 'pointer', boxShadow: wrong ? 'none' : '0 12px 22px -16px rgba(60,40,20,.5)' }}>
                        <span className="dc-label block" style={{ color: wrong ? K.faint : K.green }}>{isApproval ? c.first + '’s decision' : 'Evidence card'}</span>
                        <span className="dc-display block" style={{ fontSize: 20, lineHeight: 1.2, marginTop: 6, color: wrong ? K.faint : K.ink }}>{o.title}</span>
                        <span className="block" style={{ fontSize: 16, lineHeight: 1.4, marginTop: 4, color: wrong ? K.faint : K.muted }}>{o.detail}</span>
                        {wrong ? <span className="block" style={{ marginTop: 12 }}><Stamp text={isApproval ? 'ON HOLD' : 'NOT ADMISSIBLE'} color={K.red} size="13px" /></span> : null}
                      </button>
                    );
                  })}
                </div>
                {fb && !fb.ok ? (
                  <div key={fb.id} className="dc-in flex items-start gap-3" style={{ marginTop: 12 }}>
                    <Avatar who={isApproval ? 'crane' : 'owl'} size={42} />
                    <p style={{ fontSize: 17, lineHeight: 1.5, margin: '6px 0 0' }}>{isApproval ? <span><b>Docket:</b> {fb.text}</span> : <span><b>Owl:</b> Not admissible. {fb.text} Try another card.</span>}</p>
                  </div>
                ) : null}
              </div>
            ) : null}
            {choice && mode === 'argue' && picked ? <div className="dc-in" style={{ marginTop: 10, fontSize: 16, fontWeight: 700, color: K.green }}>{isApproval ? '✓ Approved by ' + c.first + '. Docket can go ahead.' : '✓ Admitted' + (res[bkey].wrong.length ? '' : ' on the first try') + '.'}</div> : null}
            {isApproval && mode === 'watch' ? <div className="dc-in" style={{ marginTop: 10, fontSize: 16, fontWeight: 700, color: K.green }}>✓ Approved by {c.first}. In “Argue it yourself”, you make this call.</div> : null}
            {round.meta.id === 'money' ? <div style={{ marginTop: 12, fontSize: 15, color: K.muted, lineHeight: 1.5 }}>Simulated bank feed: no bank is connected in this prototype. In the full Docket, the Ledger reads deposits from a read-only bank feed (Capital One’s Nessie sandbox in our build).</div> : null}
            {round.meta.id === 'call' && !isApproval ? <div style={{ marginTop: 12, fontSize: 15, color: K.muted, lineHeight: 1.5 }}>Simulated call: no real call is placed and nothing is sent.</div> : null}
          </div>
        )}
        {transcript.length ? (
          <details style={{ borderTop: '1px solid ' + K.rule }}>
            <summary className="flex items-center justify-between gap-3" style={{ padding: '10px 2px 2px', fontSize: 16, fontWeight: 600 }}>
              <span>Round transcript · {transcript.length} {transcript.length === 1 ? 'line' : 'lines'}</span><span className="dc-chev" aria-hidden>›</span>
            </summary>
            <ol style={{ margin: 0, padding: '6px 0 0', listStyle: 'none' }}>
              {transcript.map(t => (
                <li key={t.i} className="flex gap-3" style={{ padding: '7px 0', borderTop: '1px solid ' + K.rule }}>
                  <span style={{ fontSize: 16, fontWeight: 700, minWidth: 92, flexShrink: 0 }}>{whoName(t.who, c)}</span>
                  <span style={{ fontSize: 16, lineHeight: 1.5, color: K.muted }}>{t.text}</span>
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </div>
    );
  }

  return (
    <div ref={rootRef} className="dc-root w-full" style={{ position: 'relative', height: 'var(--mana-app-height, 82vh)', minHeight: 560, overflow: 'hidden', borderRadius: 10, background: '#5A4330' }}>
      <link rel="stylesheet" href={FONT_HREF} />
      <style>{CSS}</style>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }} />
      <div aria-hidden style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden', zIndex: 2 }}>
        {CHAR_ORDER.map(w => (
          <div key={w} ref={el => { labelRefs.current[w] = el; }} className="dc3-label" style={{ opacity: 0 }}>
            <span className="n">{CAST[w].name}<span className="r"> · {CAST[w].role}</span></span>
            {phase === 'title' ? <span className="d">{CAST[w].note}</span> : null}
          </div>
        ))}
      </div>

      <div style={{ position: 'absolute', top: 10, left: 10, right: 10, zIndex: 6, pointerEvents: 'none' }} className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="dc3-chip" style={{ pointerEvents: 'auto', padding: '7px 14px', fontSize: 16, lineHeight: 1.3 }}>
            <span className="dc-display" style={{ fontWeight: 600, fontSize: 18 }}>Docket: The Case</span>
            {phase !== 'title' ? <span style={{ color: K.muted, fontWeight: 500 }}> · {c.name}{phase === 'play' ? ' · ' + (mode === 'watch' ? 'Watching' : 'Arguing') : ''}</span> : null}
          </span>
          <span style={{ pointerEvents: 'auto' }}>{Honest()}</span>
        </div>
        {phase === 'play' ? (
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="dc3-chip grid grid-cols-3" style={{ pointerEvents: 'auto', borderRadius: 10, padding: '8px 12px', columnGap: 10, minWidth: 'min(100%, 430px)', flex: '1 1 300px', maxWidth: 520 }}>
              {ROUND_META.map((m, i) => {
                const skipped = !c.exempt && i > 0;
                const state = skipped ? (roundDone ? 'skipped' : 'later') : i < ri || (i === ri && roundDone) ? 'done' : i === ri ? 'now' : 'later';
                return (
                  <div key={m.id} className="min-w-0">
                    <div style={{ height: 4, borderRadius: 4, background: state === 'done' ? K.green : state === 'now' ? K.ink : K.rule, transition: 'background .4s' }} />
                    <div style={{ marginTop: 6, fontSize: 14, lineHeight: 1.25, fontWeight: state === 'now' ? 700 : 600, color: state === 'now' ? K.ink : state === 'done' ? K.green : K.faint }}>
                      {state === 'done' ? '✓ ' : (i + 1) + ' '}{m.title}{state === 'skipped' ? ' · skipped' : ''}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-2 flex-wrap" style={{ pointerEvents: 'auto' }}>
              <button type="button" className="dc-ghost" onClick={() => setPlaying(!playing)} aria-pressed={!playing}>{playing ? 'Pause' : 'Play'}</button>
              <button type="button" className="dc-ghost" onClick={() => (roundDone ? nextRound() : advance())} disabled={waiting}>Next →</button>
              <button type="button" className="dc-ghost" onClick={() => setPhase('title')}>Exit</button>
            </div>
          </div>
        ) : null}
      </div>

      {!ready && !err3d ? <div className="dc-mono" style={{ position: 'absolute', top: '32%', left: 0, right: 0, textAlign: 'center', color: '#F3ECDF', fontSize: 14, letterSpacing: '.12em', zIndex: 1 }}>FOLDING THE PAPER WORLD…</div> : null}
      {err3d ? <div style={{ position: 'absolute', top: 110, left: 16, right: 16, zIndex: 6, color: '#FBF7EF', fontSize: 16, lineHeight: 1.5, maxWidth: 560 }}>The 3D desk couldn’t start on this device ({err3d}). The case still plays in the card below.</div> : null}

      <div ref={panelRef} className="dc3-panel">{panel}</div>
    </div>
  );
}


export default UserDiv;
