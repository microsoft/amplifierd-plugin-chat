# Shell Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct shell command execution to Amplifier Chat via `!` prefix with animated input transformation and output rendered as synthetic bash tool calls.

**Architecture:** The frontend `InputArea` component detects `!` prefix and toggles a `shellMode` state that applies CSS class changes for the Terminal Morph animation. On send, shell commands POST to a new `/chat/api/sessions/{id}/shell` backend endpoint that spawns a subprocess, streams output via SSE using the existing `tool:pre`/`tool:post` event format, and injects the result into the session transcript. The existing `ToolCallCard` renders the output with a `(user)` badge.

**Tech Stack:** Preact + HTM (frontend, no build step), FastAPI (backend), CSS transitions (animation), asyncio.subprocess (command execution)

**Spec:** `docs/superpowers/specs/2026-03-23-shell-mode-design.md`

---

### Task 1: Add CSS for Shell Mode Input Transformation

Add the shell mode CSS tokens, `.shell-mode` styles, and transition animations to the existing `<style>` block. This is pure CSS — no JS changes yet.

**Files:**
- Modify: `src/chat_plugin/static/index.html` (CSS section, lines ~11-47 for tokens, ~1742-1812 for input area styles)

- [ ] **Step 1: Add shell mode CSS tokens to `:root`**

In the `:root` block (around line 11), add after `--action-btn-color-hover`:

```css
      /* Shell mode tokens */
      --shell-border: var(--accent-green);
      --shell-glow: rgba(34, 197, 94, 0.15);
      --shell-font: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
```

And in the `body[data-theme="light"]` block (around line 49), add:

```css
      --shell-glow: rgba(22, 163, 74, 0.1);
```

- [ ] **Step 2: Add transition properties to existing input elements**

On `#message-input` (line ~1780), add a `transition` property:

```css
    #message-input {
      /* ... existing styles ... */
      transition: border-color 200ms ease-out, box-shadow 200ms ease-out, font-family 200ms ease-out;
    }
```

On `.send-btn` (line ~1810), add:

```css
    .send-btn {
      background: var(--accent-blue);
      color: white;
      transition: background-color 200ms ease-out;
    }
```

- [ ] **Step 3: Add `.shell-mode` modifier styles**

After the existing `#message-input:focus` rule (~line 1796), add:

```css
    /* Shell mode input transformation */
    .shell-mode #message-input {
      border-color: var(--shell-border);
      box-shadow: 0 0 8px var(--shell-glow);
      font-family: var(--shell-font);
      padding-left: 28px;
    }
    .shell-mode #message-input:focus {
      border-color: var(--shell-border);
    }
    .shell-mode .send-btn {
      background: var(--accent-green);
    }

    /* $ prompt pseudo-element */
    .shell-mode .input-row {
      position: relative;
    }
    .shell-mode .shell-prompt {
      position: absolute;
      left: 56px; /* after attach button (48px) + gap (8px) */
      top: 50%;
      transform: translateY(-50%);
      font-family: var(--shell-font);
      font-size: 14px;
      color: var(--text-muted);
      pointer-events: none;
      z-index: 1;
      opacity: 1;
      transition: opacity 150ms ease-in;
    }
```

- [ ] **Step 4: Add user-initiated badge style for ToolCallCard**

After the existing `.tool-origin-badge` styles, add:

```css
    .tool-user-badge {
      font-size: 10px;
      color: var(--text-muted);
      margin-left: 4px;
      font-weight: 400;
    }
```

- [ ] **Step 5: Verify CSS by visual inspection**

Open the app in a browser, inspect the `#input-area` element, and manually add `class="shell-mode"` to verify the styles apply correctly. Check both dark and light themes.

- [ ] **Step 6: Commit**

```bash
git add src/chat_plugin/static/index.html
git commit -m "feat(shell-mode): add CSS tokens, transitions, and shell-mode styles"
```

---

### Task 2: Add Shell Mode State and Input Detection to InputArea

Wire up the `!` prefix detection in `handleInput`, add `shellMode` state, and modify `doSend` to route shell commands to a different handler.

**Files:**
- Modify: `src/chat_plugin/static/index.html` (InputArea component, starts at line ~4845)

- [ ] **Step 1: Add `shellMode` state and `onShellExecute` prop**

In the `InputArea` function (line ~4845), add state:

```js
    const [shellMode, setShellMode] = useState(false);
```

Add `onShellExecute` to the destructured props:

```js
  function InputArea({ onSend, onStop, onQueueMessage, onShellExecute, executing, shouldQueue, viewMode, setViewMode, activeKey, labsVoice }) {
```

- [ ] **Step 2: Modify `handleInput` to detect `!` prefix**

In `handleInput` (line ~4988), add shell mode detection alongside the existing `/` slash detection:

```js
    const handleInput = useCallback((e) => {
      autoResize();
      const val = e.target.value;
      if (val.startsWith('/')) {
        setSlashOpen(true);
        setSlashFilter(val.slice(1).toLowerCase());
        setSlashActiveIndex(0);
        setShellMode(false);
      } else if (val.startsWith('!')) {
        setShellMode(true);
        setSlashOpen(false);
        setSlashActiveIndex(0);
      } else {
        setSlashOpen(false);
        setSlashActiveIndex(0);
        setShellMode(false);
      }
    }, [autoResize]);
```

- [ ] **Step 3: Modify `doSend` to route shell commands**

In `doSend` (line ~4901), add shell mode handling before the normal send path:

```js
      // Shell mode: bypass AI, execute directly
      if (shellMode && content.startsWith('!')) {
        const command = content.slice(1).trim();
        if (command) {
          onShellExecute(command);
          ta.value = '';
          ta.style.height = 'auto';
          setShellMode(false);
        }
        return;
      }
```

Add `shellMode` and `onShellExecute` to the dependency array:

```js
    }, [onSend, onQueueMessage, onShellExecute, pendingImages, shouldQueue, shellMode]);
```

- [ ] **Step 4: Apply shell-mode class and render $ prompt**

In the InputArea JSX return (line ~5089 area), wrap `#input-area` with the shell-mode class:

Change:
```html
      <div id="input-area">
```
To:
```html
      <div id="input-area" class=${shellMode ? 'shell-mode' : ''}>
```

Inside the `<div class="input-row">`, add the `$` prompt element:

```html
        <div class="input-row">
          ${shellMode && html`<span class="shell-prompt">$</span>`}
```

- [ ] **Step 5: Update placeholder and send button label**

On the textarea, modify the placeholder:
```html
            placeholder=${shellMode ? 'command...' : (shouldQueue ? "Queue a message\u2026" : "Message\u2026 (/ for commands)")}
```

On the send button, modify the label:
```html
          <button class="input-btn send-btn" onClick=${doSend}>
            ${shellMode ? 'Run' : (shouldQueue ? 'Queue' : 'Send')}
          </button>
```

- [ ] **Step 6: Test the input transformation manually**

Open the app, type `!` — verify:
- Border turns green with glow
- Font changes to monospace
- `$` prompt appears
- Button says "Run" and is green
- Placeholder says "command..."
- Delete the `!` — verify everything reverts

- [ ] **Step 7: Commit**

```bash
git add src/chat_plugin/static/index.html
git commit -m "feat(shell-mode): add shellMode state, ! detection, and input transformation"
```

---

### Task 3: Backend Shell Execution Endpoint

Add `POST /chat/api/sessions/{session_id}/shell` that runs a command in a subprocess and streams output via SSE using the existing `tool:pre`/`tool:post` event format.

**Files:**
- Create: `src/chat_plugin/shell.py`
- Modify: `src/chat_plugin/routes.py` (add new route factory)
- Modify: `src/chat_plugin/__init__.py` (register new routes)

- [ ] **Step 1: Create `shell.py` with the shell execution logic**

Create `src/chat_plugin/shell.py`:

```python
"""Shell command execution for user-initiated ! commands."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import AsyncIterator

DEFAULT_TIMEOUT = 30


async def execute_shell_command(
    command: str,
    cwd: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> AsyncIterator[str]:
    """Execute a shell command and yield SSE-formatted events.

    Yields tool:pre, then streams output chunks, then tool:post with
    the final result and exit code.
    """
    tool_call_id = f"user_shell_{uuid.uuid4().hex[:12]}"
    resolved_cwd = cwd or str(Path.home())

    # tool:pre event
    pre_payload = {
        "name": "bash",
        "tool_call_id": tool_call_id,
        "arguments": {"command": command},
        "user_initiated": True,
    }
    yield f"event: tool:pre\ndata: {json.dumps(pre_payload)}\n\n"

    start = time.monotonic()
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    returncode = -1

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=resolved_cwd,
        )

        try:
            assert proc.stdout is not None
            while True:
                chunk = await asyncio.wait_for(
                    proc.stdout.read(4096),
                    timeout=max(0.1, timeout - (time.monotonic() - start)),
                )
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                stdout_parts.append(text)
                # Stream partial output
                partial = {
                    "tool_call_id": tool_call_id,
                    "partial_output": text,
                }
                yield f"event: tool:output\ndata: {json.dumps(partial)}\n\n"

        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            stdout_parts.append(f"\n[killed: timeout after {timeout}s]")
            returncode = -9

        if returncode != -9:
            await proc.wait()
            returncode = proc.returncode or 0

    except Exception as exc:
        stdout_parts.append(f"Error executing command: {exc}")
        returncode = 1

    elapsed = round(time.monotonic() - start, 2)
    full_output = "".join(stdout_parts)

    # tool:post event
    post_payload = {
        "name": "bash",
        "tool_call_id": tool_call_id,
        "result": full_output,
        "error": returncode != 0,
        "returncode": returncode,
        "elapsed": elapsed,
        "user_initiated": True,
    }
    yield f"event: tool:post\ndata: {json.dumps(post_payload)}\n\n"
```

- [ ] **Step 2: Add shell route factory in `routes.py`**

At the bottom of `routes.py` (before `create_static_routes`), add:

```python
def create_shell_routes(session_manager: Any) -> APIRouter:
    """User-initiated shell command execution."""
    from starlette.responses import StreamingResponse

    from chat_plugin.shell import execute_shell_command

    router = APIRouter(prefix="/chat", tags=["chat-shell"])

    @router.post("/api/sessions/{session_id}/shell")
    async def execute_shell(session_id: str, body: dict):
        command = body.get("command", "").strip()
        if not command:
            raise HTTPException(status_code=400, detail="Empty command")

        # Resolve CWD from session metadata
        cwd = body.get("cwd") or None

        async def event_stream():
            async for event in execute_shell_command(command, cwd=cwd):
                yield event

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
```

- [ ] **Step 3: Register shell routes in `__init__.py`**

In `__init__.py`, add the import and registration:

```python
    from chat_plugin.routes import (
        create_command_routes,
        create_config_routes,
        create_fork_routes,
        create_history_routes,
        create_pin_routes,
        create_shell_routes,   # <-- add
        create_static_routes,
    )
```

And after the existing `router.include_router(...)` calls:

```python
    router.include_router(create_shell_routes(state.session_manager))
```

- [ ] **Step 4: Test backend endpoint with curl**

```bash
curl -N -X POST https://0.0.0.0:8410/chat/api/sessions/test/shell \
  -H 'Content-Type: application/json' \
  -d '{"command": "echo hello world", "cwd": "/tmp"}' \
  --insecure
```

Expected: SSE stream with `event: tool:pre`, `event: tool:output`, `event: tool:post`

- [ ] **Step 5: Commit**

```bash
git add src/chat_plugin/shell.py src/chat_plugin/routes.py src/chat_plugin/__init__.py
git commit -m "feat(shell-mode): add backend /shell endpoint with SSE streaming"
```

---

### Task 4: Wire Frontend Shell Execution to Backend SSE

Connect the `onShellExecute` callback in `ChatApp` to the backend `/shell` endpoint, consume the SSE events, and inject them into the existing chrono items for rendering by `ToolCallCard`.

**Files:**
- Modify: `src/chat_plugin/static/index.html` (ChatApp component and API client)

- [ ] **Step 1: Add `shellExecute` to the API client**

In the API client object (around line ~2400), add:

```js
    async shellStream(sessionId, command, cwd) {
      const resp = await fetch(`${API_BASE}/sessions/${sessionId}/shell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, cwd }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err?.detail || `Shell execution failed: HTTP ${resp.status}`);
      }
      return resp;
    },
```

- [ ] **Step 2: Add `handleShellExecute` in ChatApp**

In the `ChatApp` component, add a handler that:
1. Calls `api.shellStream()`
2. Reads SSE events from the response
3. On `tool:pre`: creates a new tool_call chrono item (running state)
4. On `tool:output`: appends partial output to the item's result
5. On `tool:post`: finalizes the item with full result and status

```js
    const handleShellExecute = useCallback(async (command) => {
      if (!activeKey) return;
      const session = sessions.find(s => s.id === activeKey);
      const cwd = session?.cwd || '~';

      try {
        const resp = await api.shellStream(activeKey, command, cwd);
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentItem = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let eventType = null;
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ') && eventType) {
              const data = JSON.parse(line.slice(6));
              if (eventType === 'tool:pre') {
                currentItem = {
                  id: 'shell_' + Date.now(),
                  type: 'tool_call',
                  toolName: data.name,
                  toolCallId: data.tool_call_id,
                  arguments: data.arguments,
                  toolStatus: 'running',
                  result: '',
                  userInitiated: true,
                  streaming: true,
                  order: Date.now(),
                };
                setChronoItems(prev => [...prev, currentItem]);
              } else if (eventType === 'tool:output' && currentItem) {
                currentItem = { ...currentItem, result: currentItem.result + data.partial_output };
                setChronoItems(prev =>
                  prev.map(it => it.toolCallId === currentItem.toolCallId ? currentItem : it)
                );
              } else if (eventType === 'tool:post' && currentItem) {
                currentItem = {
                  ...currentItem,
                  result: data.result,
                  toolStatus: data.error ? 'error' : 'complete',
                  resultError: data.error ? data.result : null,
                  streaming: false,
                };
                setChronoItems(prev =>
                  prev.map(it => it.toolCallId === currentItem.toolCallId ? currentItem : it)
                );
              }
              eventType = null;
            }
          }
        }
      } catch (err) {
        console.error('[shell] execution error:', err);
      }
    }, [activeKey, sessions]);
```

- [ ] **Step 3: Pass `onShellExecute` to `InputArea`**

Find where `InputArea` is rendered in `ChatApp` and add the prop:

```html
    <${InputArea}
      ...existing props...
      onShellExecute=${handleShellExecute}
    />
```

- [ ] **Step 4: Add `(user)` badge to ToolCallCard**

In the `ToolCallCard` component (line ~3870), after the tool name span, add:

```html
          <span class="tool-name">${item.toolName || 'tool'}</span>
          ${item.userInitiated && html`<span class="tool-user-badge">(user)</span>`}
```

- [ ] **Step 5: Test end-to-end**

Type `!echo hello world` in the chat input. Verify:
- Input transforms to shell mode
- On send, a tool call card appears with "bash (user)" header
- Output shows "hello world"
- Card is expandable/collapsible
- Try `!ls -la` to test longer output
- Try `!nonexistent_command` to test error state (red styling)

- [ ] **Step 6: Commit**

```bash
git add src/chat_plugin/static/index.html
git commit -m "feat(shell-mode): wire frontend to backend SSE, render via ToolCallCard"
```

---

### Task 5: Polish and Edge Cases

Handle edge cases, clean up, and verify both themes.

**Files:**
- Modify: `src/chat_plugin/static/index.html`

- [ ] **Step 1: Handle shell mode during active AI execution**

Shell commands should still work even when the AI is executing (the `executing` state is true). The `doSend` shell path should bypass the queue and executing checks. Verify this works.

- [ ] **Step 2: Prevent shell mode when textarea has content before `!`**

If the user types text then moves cursor to beginning and types `!`, it should NOT activate shell mode. Only activate when `!` is literally the first character and the value starts with `!`.

- [ ] **Step 3: Test light theme**

Toggle to light theme and verify:
- Green border has good contrast
- Glow is visible but subtle
- `$` prompt is readable
- "Run" button green works
- Tool card with `(user)` badge renders correctly

- [ ] **Step 4: Test mobile viewport**

Resize to iPhone dimensions and verify:
- Shell mode input transformation doesn't break layout
- `$` prompt doesn't overlap with text
- "Run" button doesn't wrap awkwardly

- [ ] **Step 5: Commit final polish**

```bash
git add -A
git commit -m "feat(shell-mode): edge case handling and theme polish"
```
