from ops_cli.integrations.sessionhub import SessionHubSceneManager


def test_sessionhub_scene_manager_requires_root() -> None:
    manager = SessionHubSceneManager(root="/tmp/does-not-exist-sessionhub")

    try:
        manager.check_scene("jst_erp", "order_list")
    except FileNotFoundError as exc:
        assert "SessionHub" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
