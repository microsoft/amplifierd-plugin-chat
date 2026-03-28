"""Tests for SessionManager.create() — session_cwd, prepared-bundle cache,
and tool-wrapping integration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifierd.state.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Helpers / Fakes
# ---------------------------------------------------------------------------


def _make_fake_session(session_id: str = "sess-001") -> MagicMock:
    session = MagicMock()
    session.session_id = session_id
    session.parent_id = None
    return session


def _make_prepared(session: MagicMock | None = None) -> MagicMock:
    if session is None:
        session = _make_fake_session()
    prepared = MagicMock()
    prepared.create_session = AsyncMock(return_value=session)
    return prepared


def _make_session_manager(*, projects_dir: Path | None = None) -> SessionManager:
    event_bus = MagicMock()
    settings = MagicMock()
    settings.default_bundle = None
    settings.default_working_dir = None
    # bundle_registry must be truthy for create() to not raise
    bundle_registry = MagicMock()
    return SessionManager(
        event_bus=event_bus,
        settings=settings,
        bundle_registry=bundle_registry,
        projects_dir=projects_dir,
    )


# ---------------------------------------------------------------------------
# TestCreatePassesSessionCwd
# ---------------------------------------------------------------------------


class TestCreatePassesSessionCwd:
    """create() must forward the resolved working_dir as session_cwd=Path(wd)."""

    @pytest.mark.asyncio
    async def test_create_passes_session_cwd_to_create_session(self, tmp_path):
        """session_cwd is Path(wd) where wd comes from resolve_working_dir."""
        sm = _make_session_manager()
        session = _make_fake_session()
        prepared = _make_prepared(session)

        # Pre-warm the cache so we skip the bundle-registry slow path.
        sm.set_prepared_bundle("my-bundle", prepared)

        with (
            patch(
                "amplifierd.spawn.register_spawn_capability", side_effect=ImportError
            ),
            patch("amplifierd.threading.wrap_tools_for_threading"),
        ):
            handle = await sm.create(
                bundle_name="my-bundle",
                working_dir=str(tmp_path),
            )

        prepared.create_session.assert_called_once_with(session_cwd=tmp_path)
        assert handle.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_create_expands_tilde_in_working_dir(self):
        """resolve_working_dir expands ~ to the absolute home path."""
        sm = _make_session_manager()
        session = _make_fake_session()
        prepared = _make_prepared(session)
        sm.set_prepared_bundle("my-bundle", prepared)

        with (
            patch(
                "amplifierd.spawn.register_spawn_capability", side_effect=ImportError
            ),
            patch("amplifierd.threading.wrap_tools_for_threading"),
        ):
            await sm.create(bundle_name="my-bundle", working_dir="~/some/dir")

        call_kwargs = prepared.create_session.call_args.kwargs
        assert "~" not in str(call_kwargs["session_cwd"])


# ---------------------------------------------------------------------------
# TestSessionManagerPreparedBundleCache
# ---------------------------------------------------------------------------


class TestSessionManagerPreparedBundleCache:
    """The prepared-bundle cache (set_prepared_bundle) is used as fast path."""

    @pytest.mark.asyncio
    async def test_cached_prepared_bundle_is_used(self):
        """When a PreparedBundle is pre-warmed, create() skips bundle_registry.load()."""
        sm = _make_session_manager()
        session = _make_fake_session()
        prepared = _make_prepared(session)
        sm.set_prepared_bundle("my-bundle", prepared)

        with (
            patch(
                "amplifierd.spawn.register_spawn_capability", side_effect=ImportError
            ),
            patch("amplifierd.threading.wrap_tools_for_threading"),
        ):
            handle = await sm.create(bundle_name="my-bundle")

        # The injected mock bundle_registry.load should NOT have been called
        sm._bundle_registry.load.assert_not_called()
        prepared.create_session.assert_called_once()
        assert handle.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_clear_prepared_bundle_forces_slow_path(self):
        """After clear_prepared_bundle(), the fast path is bypassed."""
        sm = _make_session_manager()
        session = _make_fake_session()
        prepared = _make_prepared(session)
        sm.set_prepared_bundle("my-bundle", prepared)
        sm.clear_prepared_bundle("my-bundle")

        # Now the slow path will run → need a real bundle_registry mock.
        bundle = MagicMock()
        bundle.prepare = AsyncMock(return_value=prepared)
        registry = MagicMock()
        registry.load = AsyncMock(return_value=bundle)
        sm._bundle_registry = registry

        with (
            patch("amplifierd.providers.load_provider_config", return_value=[]),
            patch("amplifierd.providers.inject_providers"),
            patch(
                "amplifierd.spawn.register_spawn_capability", side_effect=ImportError
            ),
            patch("amplifierd.threading.wrap_tools_for_threading"),
        ):
            handle = await sm.create(bundle_name="my-bundle")

        registry.load.assert_called_once_with("my-bundle")
        assert handle.session_id == session.session_id


# ---------------------------------------------------------------------------
# TestWrapToolsForThreadingCalledInCreate
# ---------------------------------------------------------------------------


class TestWrapToolsForThreadingCalledInCreate:
    """wrap_tools_for_threading(session) is called immediately after create_session."""

    @pytest.mark.asyncio
    async def test_wrap_tools_called_with_session(self):
        """create() calls wrap_tools_for_threading(session) after create_session."""
        sm = _make_session_manager()
        session = _make_fake_session()
        prepared = _make_prepared(session)
        sm.set_prepared_bundle("my-bundle", prepared)

        with (
            patch(
                "amplifierd.spawn.register_spawn_capability", side_effect=ImportError
            ),
            patch("amplifierd.threading.wrap_tools_for_threading") as mock_wrap,
        ):
            await sm.create(bundle_name="my-bundle")

        mock_wrap.assert_called_once_with(session)

    @pytest.mark.asyncio
    async def test_wrap_tools_called_before_register(self):
        """wrap_tools_for_threading is called before register() so the handle has wrapped tools."""
        sm = _make_session_manager()
        session = _make_fake_session()
        prepared = _make_prepared(session)
        sm.set_prepared_bundle("my-bundle", prepared)

        call_order: list[str] = []

        def record_wrap(s):
            call_order.append("wrap")

        original_register = sm.register

        def record_register(**kwargs):
            call_order.append("register")
            return original_register(**kwargs)

        sm.register = record_register  # type: ignore[method-assign]

        with (
            patch(
                "amplifierd.spawn.register_spawn_capability", side_effect=ImportError
            ),
            patch(
                "amplifierd.threading.wrap_tools_for_threading", side_effect=record_wrap
            ),
        ):
            await sm.create(bundle_name="my-bundle")

        assert "wrap" in call_order, "wrap_tools_for_threading was never called"
        assert call_order.index("wrap") < call_order.index("register"), (
            "wrap_tools_for_threading must be called before register()"
        )
