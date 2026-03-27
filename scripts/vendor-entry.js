// vendor-entry.js — esbuild entry point for vendor.js
// Bundles all third-party libraries used by the chat UI into a single file.
//
// Usage:  node scripts/build-vendor.mjs
//   or:   bash scripts/build-vendor.sh
//
// Libraries:
//   preact   — Virtual DOM (React-compatible)
//   htm      — Tagged-template JSX alternative
//   marked   — Markdown-to-HTML parser
//   dompurify — HTML sanitization (XSS protection)

import * as preact from 'preact';
import * as preactHooks from 'preact/hooks';
import htm from 'htm';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const html = htm.bind(preact.h);

window.preact = preact;
window.preactHooks = preactHooks;
window.html = html;
window.marked = marked;
window.DOMPurify = DOMPurify;
