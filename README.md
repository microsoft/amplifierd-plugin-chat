# amplifier-chat

A chat UI plugin for [amplifier-distro](https://github.com/microsoft/amplifier-distro). Adds a browser-based conversational interface for creating and managing Amplifier sessions.

## What it provides

When loaded into amplifier-distro, the plugin mounts these endpoints:

| Path | Description |
|------|-------------|
| `GET /chat/` | Single-page chat UI |
| `GET /chat/health` | Health check |
| `POST /chat/command` | Slash-command processing (`/help`, `/status`, `/clear`, etc.) |
| `GET /chat/api/sessions/history` | Discover past sessions from disk |
| `GET\|POST /chat/api/sessions/revisions` | Session change-detection for live refresh |
| `GET /chat/api/sessions/pins` | List pinned sessions |
| `POST\|DELETE /chat/api/sessions/{id}/pin` | Pin/unpin a session |

The UI uses amplifier-distro's native REST API for session lifecycle and SSE for streaming — no WebSocket required.

## Installation

If amplifier-distro is installed as a [uv tool](https://docs.astral.sh/uv/concepts/tools/), add the plugin with `--with`:

```bash
uv tool install git+https://github.com/microsoft/amplifier-distro \
  --with git+https://github.com/microsoft/amplifier-chat
```

If amplifier-distro is already installed, pass `--force` to reinstall with the plugin:

```bash
uv tool install git+https://github.com/microsoft/amplifier-distro --force \
  --with git+https://github.com/microsoft/amplifier-chat
```

Alternatively, if you manage amplifier-distro's environment directly, install the plugin with `uv pip`:

```bash
uv pip install git+https://github.com/microsoft/amplifier-chat
```

amplifier-distro discovers it automatically via the `amplifierd.plugins` entry point on next startup. Open `http://127.0.0.1:8410/chat/` once the daemon is running.

To disable the plugin without uninstalling:

```bash
amplifierd serve --disabled-plugins chat
```

## Configuration

The plugin stores pinned sessions in `~/.amplifier-chat/`. Override with:

```bash
export CHAT_PLUGIN_HOME_DIR=/path/to/chat-data
```

## Development

### Run tests

```bash
cd amplifier-chat
uv run --extra test pytest -v
```

### Run a local amplifier-distro instance with the plugin

No global install needed. The `dev` extra pulls amplifier-distro from git and runs everything in an isolated `.venv`:

```bash
cd amplifier-chat
uv run --extra dev amplifierd serve --log-level debug
```

Then open `http://127.0.0.1:8410/chat/`.

### Standalone dev server (UI only)

For iterating on the frontend without the full daemon:

```bash
cd amplifier-chat
uv run --extra dev python -m chat_plugin
```

This starts a minimal FastAPI server with mock state. The UI loads and history/pin endpoints work, but session creation and execution require the full amplifier-distro daemon.

Options:

```
--host HOST           Bind address (default: 127.0.0.1)
--port PORT           Bind port (default: 8410)
--sessions-dir PATH   Point at a real sessions directory for history scanning
--reload              Auto-restart on code changes
```

### Project structure

```
src/chat_plugin/
    __init__.py          Plugin entry point (create_router)
    __main__.py          Standalone dev server
    commands.py          Slash-command processing
    config.py            Plugin settings (home dir)
    pin_storage.py       Persistent pin state with timestamps
    routes.py            FastAPI route factories
    session_history.py   Disk-based session discovery
    static/
        index.html       Single-page React UI (Preact + HTM)
        vendor.js         Bundled Preact/HTM runtime
```

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
