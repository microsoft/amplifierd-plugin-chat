# AGENTS.md — amplifier-chat

## Vendor Bundle

The chat UI uses a vendored JavaScript bundle at
`src/chat_plugin/static/vendor.js` containing:

- **preact** 10.x — Virtual DOM
- **htm** 3.x — Tagged-template JSX
- **marked** 9.x — Markdown parser
- **DOMPurify** 3.x — HTML sanitization (XSS protection)

### Rebuilding vendor.js

```bash
bash scripts/build-vendor.sh
```

Prerequisites: Node.js >= 18. The script installs dependencies into a
local `node_modules/`, bundles them via esbuild, and writes the output
to `src/chat_plugin/static/vendor.js`.

Entry point: `scripts/vendor-entry.js`

After rebuilding, commit the updated `vendor.js`.

## Testing

```bash
uv run pytest tests/ --tb=short -q
```

Tests are Python-based (pytest) and include both backend route tests and
frontend code-pattern assertions that verify structural invariants in
`index.html`.
