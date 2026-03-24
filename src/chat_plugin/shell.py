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

    Yields tool:pre, then streams partial output chunks, then tool:post
    with the final result and exit code.
    """
    tool_call_id = f"user_shell_{uuid.uuid4().hex[:12]}"
    if not cwd:
        raise ValueError("cwd is required for shell execution")
    resolved_cwd = cwd

    # Resolve ~ in cwd
    if resolved_cwd.startswith("~"):
        resolved_cwd = str(Path(resolved_cwd).expanduser())

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
    returncode = -1

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=resolved_cwd,
        )

        assert proc.stdout is not None
        try:
            while True:
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    raise asyncio.TimeoutError
                chunk = await asyncio.wait_for(
                    proc.stdout.read(4096),
                    timeout=remaining,
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
