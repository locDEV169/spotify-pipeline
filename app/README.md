# Spotify App

React + TanStack Start + TypeScript + Tailwind CSS + shadcn/ui (Base UI). Requires Node.js >= 22.12.

```sh
cd app
npm ci
npm run dev
```

Open http://127.0.0.1:3000. Demo analytics dashboard with week selection, search,
missing-feature filtering, and CSV export. All rankings and metrics are synthetic.
Includes `GET /api/health`.
Database integration is pending; keep credentials server-side in `app/.env`.

Checks: `npm run build`, `npm run typecheck`, and `npm run test:smoke` (requires a running dev server).
Run `npm run test:demo` to check fixture filtering and summary calculations.

## Structure

```text
app/
├── src/
│   ├── routes/              # React pages and API endpoints
│   │   ├── __root.tsx       # Root layout
│   │   ├── index.tsx        # Home page
│   │   └── api/health.ts    # Health endpoint
│   ├── server/              # Server functions
│   ├── components/ui/       # Button, Select, Skeleton (shadcn / Base UI)
│   ├── components/charts/   # Demo analytics dashboard
│   ├── lib/demo-data.ts     # Synthetic chart fixtures and summaries
│   ├── lib/utils.ts         # Shared class name utility
│   ├── router.tsx          # Router configuration
│   ├── routeTree.gen.ts    # Generated route tree
│   └── styles.css          # Tailwind CSS
├── scripts/smoke.mjs       # HTTP smoke test
├── package.json
├── components.json         # shadcn configuration
├── tsconfig.json
└── vite.config.ts
```

Import UI components from `@/components/ui/button` (or `select`, `skeleton`).
Add more from `app/`: `npx shadcn@latest add dialog`.

Known issue (2026-11-18): npm audit reports 12 high-severity entries originating
from transitive picomatch; no patched release was available during setup. Recheck before deployment.
