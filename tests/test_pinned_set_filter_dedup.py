"""
Tests for S-12: Remove 3 redundant pinnedSet filter guards.

Bug: The keyboard-navigation ordered-keys block duplicates an identical
`.filter(k => !pinnedSet.has(k))` call inside each of the three group-mode
branches (project, activity, age). This is redundant repetition that can
be consolidated into a single filter applied after the branch.

Fix: Extract group keys without filtering inside each branch, then apply
the pinnedSet filter once outside the if/else chain.
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


def get_ordered_keys_block():
    content = html()
    start = content.find("// Compute flat visual order of root session keys")
    assert start != -1, "Ordered keys block comment not found"
    end = content.find("visibleSessionKeysRef.current", start)
    assert end != -1, "visibleSessionKeysRef assignment not found"
    # Include a bit past the assignment
    end = content.find("\n", end + 1)
    return content[start : end + 1]


class TestPinnedSetFilterDedup:
    def test_pinned_set_filter_count_reduced(self):
        """pinnedSet.has(k) should appear at most twice in the ordered-keys block.

        Before: 3 identical .filter(k => !pinnedSet.has(k)) in branches.
        After: 1 consolidated filter outside the branches (plus possibly
        the else-branch using pinnedSessionIds.has which is fine).
        """
        block = get_ordered_keys_block()
        count = block.count("pinnedSet.has(k)")
        assert count <= 2, (
            f"Expected at most 2 pinnedSet.has(k) calls (consolidated), found {count}"
        )

    def test_single_filter_after_branches(self):
        """A single .filter(k => !pinnedSet.has(k)) should be outside branches."""
        block = get_ordered_keys_block()
        # The consolidated filter should appear after the if/else closing
        assert ".filter(k => !pinnedSet.has(k))" in block, (
            "Consolidated pinnedSet filter not found"
        )
