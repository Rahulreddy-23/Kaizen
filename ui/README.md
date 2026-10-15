# Kaizen reviewer UI

React, TypeScript, React Router, Tailwind and Vite. Hash routes allow the compiled interface to be served
by the Python API. Fonts and assets ship with the bundle for offline use.

## Develop

Run from the repository root in separate terminals:

```bash
# API with an isolated development workspace
.venv/bin/kaizen --workspace /tmp/kaizen-ui-dev serve --port 8765
```

```bash
cd ui
npm ci
npm run dev
```

Open http://localhost:5173; Vite proxies `/api` to port 8765. Account registration and permissions are
enforced by the backend. See [accounts and deployment](../docs/hosted-collaboration.md).

## Verify and build

```bash
cd ui
npm test
npm run build
```

The build type-checks and writes `ui/dist`. `kaizen serve` serves that folder when it exists. The Docker
build compiles it in a Node stage and serves the resulting assets with the Python API on the same origin.

## Source map

- `src/api.ts` and `src/types.ts`: typed client and API contract.
- `src/components/`: shared controls, navigation, source evidence and review forms.
- `src/lib/`: session context, asynchronous loading, filtering, pagination and display helpers.
- `src/pages/`: run lists/overview, review queue/evidence, documents, learning, mining, business case,
  comparisons, terminology, action items, user administration and profile.
- `src/index.css` and `tailwind.config.js`: shared design tokens and interface styles.

Keep writes gated by server permissions, preserve query filters during review navigation, and reset
run/row-specific drafts on navigation. Refer to the [API contract](../docs/api-contract.md),
[product context](../docs/design/PRODUCT.md) and [design system](../docs/design/DESIGN.md).
