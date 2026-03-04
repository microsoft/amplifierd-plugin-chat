from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandDef:
    name: str
    description: str
    usage: str = ""


COMMANDS: list[CommandDef] = [
    CommandDef("help", "Show available commands"),
    CommandDef("status", "Show session status"),
    CommandDef("tools", "List available tools"),
    CommandDef("agents", "List available agents"),
    CommandDef("config", "Show session configuration"),
    CommandDef("cwd", "Show working directory"),
    CommandDef("clear", "Clear conversation context"),
    CommandDef("modes", "List available modes"),
    CommandDef("mode", "Activate/deactivate a mode", "/mode <name> [on|off]"),
    CommandDef("rename", "Rename the session", "/rename <name>"),
    CommandDef("fork", "Fork session at a turn", "/fork [turn]"),
]


class CommandProcessor:
    def __init__(self, *, session_manager: Any, event_bus: Any) -> None:
        self._session_manager = session_manager
        self._event_bus = event_bus

    def process_input(self, text: str) -> tuple[str, dict]:
        text = text.strip()
        if text.startswith("/"):
            parts = text[1:].split(None, 1)
            command = parts[0] if parts else ""
            args = parts[1].split() if len(parts) > 1 else []
            return "command", {"command": command, "args": args, "raw": text}
        return "prompt", {"text": text}

    def handle_command(self, command: str, args: list[str], *, session_id: str | None) -> dict:
        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            return {"type": "error", "data": {"message": f"Unknown command: /{command}"}}
        return handler(args, session_id=session_id)

    def _cmd_help(self, args: list[str], **_: Any) -> dict:
        return {
            "type": "help",
            "data": {
                "commands": [
                    {"name": f"/{c.name}", "description": c.description, "usage": c.usage}
                    for c in COMMANDS
                ],
            },
        }
