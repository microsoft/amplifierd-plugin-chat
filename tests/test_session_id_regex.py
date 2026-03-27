"""Tests for unified session ID regex (S-03).

Verifies that VALID_SESSION_ID_RE is defined once in session_history.py,
imported (not redefined) in routes.py, and that the pattern correctly
accepts/rejects session IDs.
"""

from chat_plugin import routes, session_history


def test_session_id_regex_is_single_source_of_truth():
    """routes.VALID_SESSION_ID_RE must be the same object as session_history.VALID_SESSION_ID_RE."""
    assert hasattr(session_history, "VALID_SESSION_ID_RE"), (
        "session_history must export VALID_SESSION_ID_RE (public, no leading underscore)"
    )
    assert hasattr(routes, "VALID_SESSION_ID_RE"), (
        "routes must import VALID_SESSION_ID_RE from session_history (not define its own)"
    )
    assert routes.VALID_SESSION_ID_RE is session_history.VALID_SESSION_ID_RE, (
        "routes.VALID_SESSION_ID_RE and session_history.VALID_SESSION_ID_RE must be the same object"
    )


def test_session_id_regex_rejects_colon():
    """Colon-containing session IDs must be rejected."""
    pattern = session_history.VALID_SESSION_ID_RE
    assert pattern.fullmatch("session:id") is None, "colon must be rejected"
    assert pattern.fullmatch("abc:def") is None, "colon must be rejected"
    assert pattern.fullmatch("session:123") is None, "colon must be rejected"
    assert pattern.fullmatch(":leading-colon") is None, "leading colon must be rejected"


def test_session_id_regex_rejects_path_traversal():
    """Path traversal attempts and special chars must be rejected."""
    pattern = session_history.VALID_SESSION_ID_RE
    assert pattern.fullmatch("../etc/passwd") is None, "path traversal must be rejected"
    assert pattern.fullmatch("../../etc/shadow") is None, (
        "double traversal must be rejected"
    )
    assert pattern.fullmatch("/etc/passwd") is None, "absolute path must be rejected"
    assert pattern.fullmatch("session id") is None, "space must be rejected"
    assert pattern.fullmatch("session.id") is None, "dot must be rejected"


def test_session_id_regex_allows_valid_ids():
    """Valid session IDs using alphanumeric chars, dashes, and underscores must be accepted."""
    pattern = session_history.VALID_SESSION_ID_RE
    assert pattern.fullmatch("my-session-123") is not None, (
        "dashes and digits must be allowed"
    )
    assert pattern.fullmatch("abc_DEF_789") is not None, (
        "underscores and mixed case must be allowed"
    )
    assert pattern.fullmatch("simple") is not None, "plain alphabetic must be allowed"
    assert pattern.fullmatch("session-2024-01-01") is not None, (
        "date-like ID must be allowed"
    )
    assert pattern.fullmatch("UPPERCASE") is not None, "uppercase must be allowed"
    assert pattern.fullmatch("a") is not None, "single char must be allowed"
