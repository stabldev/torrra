from typing import Any

from torrra.app import TorrraApp
from torrra.core import updater


async def test_app_starts_update_check_on_mount(app_factory: Any, monkeypatch: Any):
    calls: list[TorrraApp] = []
    monkeypatch.setattr(
        TorrraApp, "_check_for_updates", lambda self: calls.append(self)
    )

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()

    assert calls == [app]


async def test_app_notifies_when_update_available(app_factory: Any, monkeypatch: Any):
    app = app_factory()
    notifications: list[tuple[str, dict[str, Any]]] = []

    def fake_notify(message: str, **kwargs: Any) -> None:
        notifications.append((message, kwargs))

    monkeypatch.setattr(app, "notify", fake_notify)

    async with app.run_test():
        app._notify_update_available(
            updater.UpdateInfo(version="9.9.9", install_method="uv")
        )

    assert notifications
    message, kwargs = notifications[0]
    assert message == "Update available: v9.9.9 — run `uv tool upgrade torrra`"
    assert kwargs["title"] == "Update available"


async def test_app_skips_update_check_when_disabled(
    app_factory: Any, mock_config: Any, monkeypatch: Any
):
    mock_config.set("general.update_check", "false")
    calls: list[TorrraApp] = []
    monkeypatch.setattr(
        TorrraApp, "_check_for_updates", lambda self: calls.append(self)
    )

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()

    assert calls == []


async def test_update_check_runs_on_every_app_launch(
    app_factory: Any, monkeypatch: Any
):
    calls: list[TorrraApp] = []
    monkeypatch.setattr(
        TorrraApp, "_check_for_updates", lambda self: calls.append(self)
    )

    for expected_calls in (1, 2):
        app = app_factory()
        async with app.run_test() as pilot:
            await pilot.pause()

        assert len(calls) == expected_calls
