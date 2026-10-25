# Docket: The Case

A 3D, 3-round game showing how Docket's agents fight for an F-1 student's money:
a hearing, a phone call, and the money landing in the bank. Part of Docket (Cal Hacks 13.0):
https://github.com/AnushaAgarwal27/Docket

Prototype: the call and the bank deposit are simulated. The year-count rule runs live in code,
and the quote checker searches IRS Publication 519 live through a small proxy.

## Run locally

```bash
npm install
npm run dev      # http://localhost:5173
```

## Build and deploy

```bash
npm run build    # static site in dist/
```

- **Vercel (recommended):** import the repo. `api/p519.js` becomes the IRS proxy automatically.
- **Netlify / GitHub Pages / any static host:** deploy `dist/`. Without a proxy, the live IRS check
  falls back to the copy verified Oct 24, 2026 (the app says so). To use your own proxy,
  set `VITE_IRS_PROXY=https://your-proxy/p519` before `npm run build`.

## Files

- `src/DocketCase.jsx`: the whole game (cast, script, rules, three.js world, UI). One file.
- `src/main.jsx`: mounts it. `src/index.css`: Tailwind + page background.
- `api/p519.js`: server-side fetch of IRS Publication 519 (Vercel function).
- `vite.config.js`: the same proxy for local dev.

Confirm with your school's international office.
