"""
Tests for S-11: Clear childToToolRef and childAgentRef in resetSubSessionState.

Bug: When starting a new session or switching sessions, resetSubSessionState
clears sub-session maps (subSessionsRef, subBlockMapRef, subNextIndexRef)
but leaves childToToolRef and childAgentRef populated with stale entries
from the previous session, causing phantom child-to-tool associations.

Fix: Add childToToolRef.current = {} and childAgentRef.current = {} inside
resetSubSessionState so all call-sites (newSession, resumeHistorySession,
switchSession) get the cleanup automatically.
"""

import pathlib

INDEX_HTML = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "chat_plugin"
    / "static"
    / "index.html"
)


def html():
    return INDEX_HTML.read_text()


def get_reset_sub_session_body():
    content = html()
    start = content.find("function resetSubSessionState()")
    assert start != -1, "resetSubSessionState function not found"
    # Find closing brace (small function)
    end = content.find("\n    }\n", start)
    assert end != -1, "End of resetSubSessionState not found"
    return content[start : end + 6]


class TestResetSubSessionChildRefs:
    def test_child_to_tool_ref_cleared(self):
        """childToToolRef.current must be reset in resetSubSessionState."""
        body = get_reset_sub_session_body()
        assert "childToToolRef.current = {}" in body, (
            "childToToolRef.current = {} not found in resetSubSessionState"
        )

    def test_child_agent_ref_cleared(self):
        """childAgentRef.current must be reset in resetSubSessionState."""
        body = get_reset_sub_session_body()
        assert "childAgentRef.current = {}" in body, (
            "childAgentRef.current = {} not found in resetSubSessionState"
        )
