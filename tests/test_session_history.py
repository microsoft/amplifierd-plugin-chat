import json

from chat_plugin.session_history import scan_session_revisions, scan_sessions


def test_scan_sessions_none_dir():
    sessions, total = scan_sessions(None)
    assert sessions == []
    assert total == 0


def test_scan_sessions_empty_dir(tmp_path):
    sessions, total = scan_sessions(tmp_path)
    assert sessions == []
    assert total == 0


def test_scan_sessions_with_transcript(tmp_path):
    session_dir = tmp_path / "sess-abc"
    session_dir.mkdir()
    transcript = session_dir / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"role": "user", "content": "Hello"}) + "\n"
        + json.dumps({"role": "assistant", "content": "Hi"}) + "\n",
        encoding="utf-8",
    )
    results, total = scan_sessions(tmp_path)
    assert total == 1
    assert len(results) == 1
    row = results[0]
    assert row["session_id"] == "sess-abc"
    assert row["message_count"] == 2
    assert row["last_user_message"] == "Hello"
    assert row["revision"]  # non-empty


def test_scan_sessions_with_metadata(tmp_path):
    session_dir = tmp_path / "sess-xyz"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text(
        json.dumps({"role": "user", "content": "test"}) + "\n",
        encoding="utf-8",
    )
    (session_dir / "metadata.json").write_text(
        json.dumps({
            "name": "My Session",
            "description": "A test session",
            "parent_id": "sess-parent",
        }),
        encoding="utf-8",
    )
    results, total = scan_sessions(tmp_path)
    assert total == 1
    assert len(results) == 1
    row = results[0]
    assert row["name"] == "My Session"
    assert row["description"] == "A test session"
    assert row["parent_session_id"] == "sess-parent"


def test_scan_session_revisions(tmp_path):
    session_dir = tmp_path / "sess-rev"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text(
        json.dumps({"role": "user", "content": "hi"}) + "\n",
        encoding="utf-8",
    )
    rows = scan_session_revisions(tmp_path)
    assert len(rows) == 1
    assert rows[0]["session_id"] == "sess-rev"
    assert "revision" in rows[0]
    assert "last_updated" in rows[0]


def test_scan_session_revisions_filter(tmp_path):
    for name in ["sess-a", "sess-b", "sess-c"]:
        d = tmp_path / name
        d.mkdir()
        (d / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
    rows = scan_session_revisions(tmp_path, session_ids={"sess-b"})
    assert len(rows) == 1
    assert rows[0]["session_id"] == "sess-b"


def test_scan_session_revisions_none_dir():
    assert scan_session_revisions(None) == []


def test_invalid_session_ids_skipped(tmp_path):
    (tmp_path / "valid-id").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "has spaces").mkdir()
    results, total = scan_sessions(tmp_path)
    session_ids = {r["session_id"] for r in results}
    assert "valid-id" in session_ids
    assert ".hidden" not in session_ids
    assert "has spaces" not in session_ids


def test_scan_sessions_pagination(tmp_path):
    """Phase-1 mtime sort + windowed read: offset/limit respected."""
    import time

    for name in ["sess-oldest", "sess-middle", "sess-newest"]:
        d = tmp_path / name
        d.mkdir()
        (d / "transcript.jsonl").write_text(
            '{"role": "user", "content": "hi"}\n', encoding="utf-8"
        )
        time.sleep(0.01)  # ensure distinct mtimes

    # First page: limit=2, offset=0 → 2 most-recent sessions
    page, total = scan_sessions(tmp_path, limit=2, offset=0)
    assert total == 3
    assert len(page) == 2
    assert page[0]["session_id"] == "sess-newest"
    assert page[1]["session_id"] == "sess-middle"

    # Second page: limit=2, offset=2 → 1 remaining session
    page2, total2 = scan_sessions(tmp_path, limit=2, offset=2)
    assert total2 == 3
    assert len(page2) == 1
    assert page2[0]["session_id"] == "sess-oldest"


def test_scan_sessions_total_count(tmp_path):
    """total_count equals the number of valid session directories."""
    for name in ["sess-a", "sess-b", "sess-c"]:
        d = tmp_path / name
        d.mkdir()
        (d / "transcript.jsonl").write_text(
            '{"role": "user", "content": "x"}\n', encoding="utf-8"
        )

    _, total = scan_sessions(tmp_path)
    assert total == 3

    # Offset beyond all results still reports correct total
    page, total2 = scan_sessions(tmp_path, limit=10, offset=100)
    assert total2 == 3
    assert page == []
