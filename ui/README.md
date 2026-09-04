# Kaizen Cross-Check — reviewer UI

Static React front end for the local Kaizen API (`docs/api-contract.md`). Vite + React 18 + TypeScript + Tailwind; no UI kit, no charting library. Hash routing (`#/…`) so the bundle works from the backend's static mount.

## Develop

```bash
# terminal 1 — API on 127.0.0.1:8765
cd .. && .venv/bin/kaizen --workspace /tmp/kaizen-ui-ws serve --port 8765

# terminal 2 — Vite dev server on http://localhost:5173 (proxies /api to 8765)
cd ui && npm install && npm run dev
```

Open http://localhost:5173, click **Load demo dataset** on the Runs page.

## Build

```bash
cd ui && npm run build     # type-checks (tsc --noEmit) then writes ui/dist
```

`kaizen serve` mounts `ui/dist` at `/` automatically when it exists (restart the server after the first build). All API calls use relative `/api/...` URLs.

## Layout

- `src/api.ts` — typed client, one function per endpoint; `src/types.ts` — contract types.
- `src/lib/reviewer.tsx` — reviewer identity (name, slot 1/2, blind) in `localStorage`; `src/lib/queue.ts` — review-queue filter state in the URL.
- `src/components/` — badges (classification/severity/state/decision), `PageImage` (page PNG + client-side bbox outline, scale = rendered px / natural px × 110/72), `EvidenceCard`, `DecisionPanel`, `RowActions` (save as relationship, action item), `Layout`.
- `src/pages/` — one file per route: Runs, Dashboard, ReviewQueue, Evidence, Documents, Document (extraction verification), Terminology, Mining, ActionItems, BusinessCase.

Routes: `#/`, `#/runs/:runId`, `#/runs/:runId/review`, `#/runs/:runId/rows/:rowId`, `#/runs/:runId/documents[/:docId]`, `#/runs/:runId/mining`, `#/runs/:runId/business`, `#/terminology`, `#/action-items`.
