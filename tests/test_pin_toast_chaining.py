"""
Tests for S-09: Chain toast on pin promise.

Bug: In the command palette's pin-session handler, showToast is called
synchronously right after handleTogglePin, before the async pin API call
completes. If the API call fails, the user still sees a success toast.

Fix: Chain showToast on the handleTogglePin promise using .then() so
the toast only appears after the pin/unpin operation succeeds.
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


def get_pin_session_handler():
    content = html()
    start = content.find("'pin-session':")
    assert start != -1, "pin-session command not found"
    # Find the handler block
    end = content.find("'rename-session':", start)
    assert end != -1, "rename-session command not found (used as end marker)"
    return content[start:end]


class TestPinToastChaining:
    def test_toast_chained_on_promise(self):
        """showToast must be chained via .then() on handleTogglePin."""
        handler = get_pin_session_handler()
        assert ".then(" in handler and "showToast" in handler, (
            "showToast should be chained via .then() on handleTogglePin"
        )

    def test_no_synchronous_toast_after_toggle(self):
        """showToast must not appear as a bare statement after handleTogglePin."""
        handler = get_pin_session_handler()
        # The old pattern: handleTogglePin(...); followed by showToast on next line
        # The new pattern: handleTogglePin(...).then(() => showToast(...))
        lines = handler.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("showToast(") and "isPinned" in stripped:
                # This line should be inside a .then(), not standalone
                prev_lines = "\n".join(lines[max(0, i - 3) : i + 1])
                assert ".then(" in prev_lines, (
                    "showToast with isPinned should be inside .then(), not standalone"
                )
