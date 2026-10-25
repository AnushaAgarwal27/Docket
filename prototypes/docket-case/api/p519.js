// Vercel serverless function: fetches IRS Publication 519 server-side so the browser can read it.
// Netlify/Cloudflare: same idea, return the HTML of https://www.irs.gov/publications/p519.
export default async function handler(req, res) {
  try {
    const r = await fetch('https://www.irs.gov/publications/p519', { headers: { 'User-Agent': 'docket-the-case' } });
    const html = await r.text();
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=86400');
    res.status(r.ok ? 200 : 502).send(html);
  } catch (e) {
    res.status(502).send('IRS.gov unreachable');
  }
}
