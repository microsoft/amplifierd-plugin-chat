"""
Tests for S-10: Remove duplicate activeKeyRef assignment in switchSession.

Bug: switchSession sets activeKeyRef.current = key twice — once before
loading target data and again after. The first (premature) assignment
can cause race conditions if any intermediate code reads activeKeyRef
before session state is fully restored.

Fix: Remove the first assignment (keep only the one right before setActiveKey).
"""

import pathlib
import re

INDEX_HTML = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "chat_plugin"
    / "static"
    / "index.html"
)


def html():
    return INDEX_HTML.read_text()


class TestSwitchSessionActiveKeyRef:
    def _get_switch_session_body(self):
        content = html()
        # Find the switchSession function (the non-history one)
        marker = "// Save current session's messages"
        start = content.find(marker)
        assert start != -1, "switchSession save block not found"
        # Back up to find the function start
        func_start = content.rfind("const switchSession", start - 500, start)
        if func_start == -1:
            func_start = content.rfind("function switchSession", start - 500, start)
        # Find end of function
        end = content.find("}, [", start)
        assert end != -1, "switchSession end not found"
        return content[start:end]

    def test_single_active_key_ref_assignment(self):
        """activeKeyRef.current = key should appear exactly once in switchSession."""
        body = self._get_switch_session_body()
        count = len(re.findall(r"activeKeyRef\.current\s*=\s*key", body))
        assert count == 1, (
            f"Expected exactly 1 activeKeyRef.current = key in switchSession, found {count}"
        )

    def test_active_key_ref_near_set_active_key(self):
        """The single activeKeyRef assignment must be near setActiveKey(key)."""
        body = self._get_switch_session_body()
        ref_pos = body.find("activeKeyRef.current = key")
        set_pos = body.find("setActiveKey(key)")
        assert ref_pos != -1, "activeKeyRef.current = key not found"
        assert set_pos != -1, "setActiveKey(key) not found"
        assert abs(ref_pos - set_pos) < 100, (
            "activeKeyRef assignment should be near setActiveKey call"
        )
