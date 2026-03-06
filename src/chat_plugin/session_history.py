"""Session history — scans amplifierd's sessions_dir to discover past sessions.

Adapted from amplifier-distro's session_history.py for amplifierd's flat
directory layout:

    sessions_dir/
        {session_id}/transcript.jsonl
        {session_id}/metadata.json

Schema (one dict per session in scan_sessions() output):
    session_id: str             — session directory name
    cwd: str|None               — working directory from session-info.json
    parent_session_id: str|None — parent session id from metadata.json
    spawn_agent: str|None       — spawned agent name from metadata.json
    message_count: int          — number of transcript lines with a 'role' key
    last_user_message: str|None — last user message text, truncated to 120 chars
    last_updated: str           — ISO-format mtime of transcript.jsonl
    revision: str               — mtime_ns:size signature for stale-change detection
    name: str|None              — session name from metadata.json
    description: str|None       — session description from metadata.json
"""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRANSCRIPT_FILENAME = "transcript.jsonl"
METADATA_FILENAME = "metadata.json"
SESSION_INFO_FILENAME = "session-info.json"

_VALID_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _session_revision_signature(session_dir: Path) -> tuple[str, str]:
    """Return (last_updated_iso, revision_signature) for one session directory."""
    transcript_path = session_dir / TRANSCRIPT_FILENAME
    stat_target = transcript_path if transcript_path.exists() else session_dir
    try:
        stat = stat_target.stat()
        last_updated = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
        mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
        revision = f"{int(mtime_ns)}:{int(stat.st_size)}"
        return last_updated, revision
    except OSError:
        return datetime.now(tz=UTC).isoformat(), "0:0"


def _read_session_meta(session_dir: Path) -> dict[str, Any]:
    """Extract lightweight metadata from a single session directory."""
    # Try to read CWD from session-info.json
    cwd: str | None = None
    info_path = session_dir / SESSION_INFO_FILENAME
    try:
        data = json.loads(info_path.read_text(encoding="utf-8"))
        raw = data.get("working_dir")
        if isinstance(raw, str) and raw:
            normalized = os.path.normpath(raw)
            if os.path.isabs(normalized) and len(normalized) <= 4096:
                cwd = normalized
    except (OSError, json.JSONDecodeError):
        pass

    parent_session_id: str | None = None
    spawn_agent: str | None = None
    session_name: str | None = None
    session_description: str | None = None
    metadata_path = session_dir / METADATA_FILENAME
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if isinstance(metadata, dict):
            raw_parent = metadata.get("parent_id") or metadata.get(
                "parent_session_id"
            )
            if (
                isinstance(raw_parent, str)
                and raw_parent
                and _VALID_SESSION_ID_RE.fullmatch(raw_parent)
            ):
                parent_session_id = raw_parent
            raw_agent = metadata.get("agent_name")
            if isinstance(raw_agent, str) and raw_agent:
                spawn_agent = raw_agent
            raw_name = metadata.get("name")
            if isinstance(raw_name, str) and raw_name:
                session_name = raw_name
            raw_desc = metadata.get("description")
            if isinstance(raw_desc, str) and raw_desc:
                session_description = raw_desc
            # Fallback: CWD from metadata if not found in session-info.json
            if cwd is None:
                raw_cwd = metadata.get("working_dir")
                if isinstance(raw_cwd, str) and raw_cwd:
                    normalized = os.path.normpath(raw_cwd)
                    if os.path.isabs(normalized) and len(normalized) <= 4096:
                        cwd = normalized
    except (OSError, json.JSONDecodeError):
        pass

    transcript_path = session_dir / TRANSCRIPT_FILENAME
    message_count = 0
    last_user_message: str | None = None
    last_updated, revision = _session_revision_signature(session_dir)

    if transcript_path.exists():
        try:
            with transcript_path.open(encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(entry, dict) or not entry.get("role"):
                        continue
                    message_count += 1
                    if entry["role"] == "user":
                        content = entry.get("content", "")
                        if isinstance(content, str):
                            last_user_message = content[:120]
                        elif isinstance(content, list):
                            for block in content:
                                if (
                                    isinstance(block, dict)
                                    and block.get("type") == "text"
                                ):
                                    last_user_message = (
                                        block.get("text") or ""
                                    )[:120]
                                    break
        except OSError:
            logger.warning(
                "Could not read transcript at %s",
                transcript_path,
                exc_info=True,
            )

    return {
        "session_id": session_dir.name,
        "cwd": cwd,
        "parent_session_id": parent_session_id,
        "spawn_agent": spawn_agent,
        "message_count": message_count,
        "last_user_message": last_user_message,
        "last_updated": last_updated,
        "revision": revision,
        "name": session_name,
        "description": session_description,
    }


def _iter_session_dirs(sessions_dir: Path) -> list[Path]:
    """Return validated session directories under sessions_dir."""
    if not sessions_dir.exists():
        return []

    try:
        children = list(sessions_dir.iterdir())
    except OSError:
        logger.warning(
            "Could not list sessions at %s", sessions_dir, exc_info=True
        )
        return []

    session_dirs: list[Path] = []
    for child in children:
        if not child.is_dir():
            continue
        if not _VALID_SESSION_ID_RE.fullmatch(child.name):
            logger.debug(
                "Skipping session dir with non-standard name: %r", child.name
            )
            continue
        session_dirs.append(child)

    return session_dirs


def _dir_mtime(session_dir: Path) -> float:
    """Return the mtime of transcript.jsonl (or directory) for cheap sorting."""
    transcript = session_dir / TRANSCRIPT_FILENAME
    target = transcript if transcript.exists() else session_dir
    try:
        return target.stat().st_mtime
    except OSError:
        return 0.0


def scan_sessions(
    sessions_dir: Path | None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Scan sessions_dir and return lightweight metadata for the requested page.

    Two-phase algorithm for efficiency at scale:
      Phase 1 — cheap stat() all session dirs (~0.03 s for 5 000 dirs).
                Sort newest-first by mtime. Record total_count.
      Phase 2 — parallel full-read of only the offset:offset+limit window.

    Returns:
        (sessions, total_count) where *sessions* is the requested page
        (already sorted newest-first) and *total_count* is the total number
        of discovered session directories (before any caller-side filtering).

    Never raises — malformed sessions are included with degraded metadata.
    """
    if sessions_dir is None:
        return [], 0

    # Phase 1: cheap stat — discover and sort without reading transcripts
    all_dirs = _iter_session_dirs(sessions_dir)
    all_dirs.sort(key=_dir_mtime, reverse=True)
    total_count = len(all_dirs)

    window = all_dirs[offset : offset + limit]
    if not window:
        return [], total_count

    # Phase 2: parallel full-reads for only the requested window
    results: list[dict[str, Any]] = []
    max_workers = min(8, len(window))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {pool.submit(_read_session_meta, d): d for d in window}
        for future in as_completed(future_map):
            session_dir = future_map[future]
            try:
                meta = future.result()
                results.append(meta)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Skipping session %s due to unexpected error",
                    session_dir,
                    exc_info=True,
                )

    # Re-sort within the window (thread pool completes out-of-order)
    results.sort(key=lambda s: s["last_updated"], reverse=True)
    return results, total_count


def scan_session_revisions(
    sessions_dir: Path | None,
    session_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return lightweight revision metadata for session directories on disk.

    Includes name/description from metadata.json so the frontend can update
    session titles without a full history fetch.
    """
    if sessions_dir is None:
        return []

    wanted = set(session_ids) if session_ids is not None else None

    rows: list[dict[str, Any]] = []
    for session_dir in _iter_session_dirs(sessions_dir):
        session_id = session_dir.name
        if wanted is not None and session_id not in wanted:
            continue
        last_updated, revision = _session_revision_signature(session_dir)
        row: dict[str, Any] = {
            "session_id": session_id,
            "last_updated": last_updated,
            "revision": revision,
        }
        # Read name/description from metadata.json for live title updates
        metadata_path = session_dir / METADATA_FILENAME
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(metadata, dict):
                if isinstance(metadata.get("name"), str) and metadata["name"]:
                    row["name"] = metadata["name"]
                if (
                    isinstance(metadata.get("description"), str)
                    and metadata["description"]
                ):
                    row["description"] = metadata["description"]
        except (OSError, json.JSONDecodeError):
            pass
        rows.append(row)

    rows.sort(key=lambda s: s["last_updated"], reverse=True)
    return rows
