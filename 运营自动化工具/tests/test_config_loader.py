from __future__ import annotations

from pathlib import Path

import pytest

from core.config_loader import DEFAULT_PATHS, _PERSONAL_PATHS, get_path, load_paths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_default_paths_only_contains_project_relative() -> None:
    """DEFAULT_PATHS should only contain project-derived paths, not personal user paths."""
    # Personal paths must NOT be in DEFAULT_PATHS — they come from paths.yaml
    for personal_key in _PERSONAL_PATHS:
        assert personal_key not in DEFAULT_PATHS, (
            f"DEFAULT_PATHS should not contain personal path: {personal_key}"
        )


def test_get_path_project_relative_works_without_yaml() -> None:
    """Project-relative paths should work even without paths.yaml override."""
    # load_paths with a nonexistent config returns DEFAULT_PATHS only
    paths = load_paths(config_path=PROJECT_ROOT / "nonexistent.yaml")
    assert "runtime_dir" in paths
    assert paths["runtime_dir"] == PROJECT_ROOT / "runtime"


def test_get_path_personal_missing_raises_with_hint(tmp_path: Path, monkeypatch) -> None:
    """Missing personal path should raise KeyError with setup hint."""
    empty_yaml = tmp_path / "paths.yaml"
    empty_yaml.write_text("# empty\n", encoding="utf-8")
    monkeypatch.setattr("core.config_loader.load_paths", lambda **kw: load_paths(config_path=empty_yaml))
    with pytest.raises(KeyError, match="paths.yaml"):
        get_path("desktop_dir")


def test_load_paths_merges_yaml_over_defaults(tmp_path: Path) -> None:
    """YAML values should override DEFAULT_PATHS."""
    yaml_file = tmp_path / "paths.yaml"
    yaml_file.write_text("runtime_dir: /tmp/custom_runtime\n", encoding="utf-8")
    paths = load_paths(config_path=yaml_file)
    assert paths["runtime_dir"] == Path("/tmp/custom_runtime")
    # Other defaults still present
    assert "logs_dir" in paths


def test_parse_simple_yaml_still_works(tmp_path: Path) -> None:
    """Regression: the existing flat YAML parser should still work."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("key1: value1\nkey2: value2\n# comment\n", encoding="utf-8")
    from core.config_loader import _parse_simple_yaml
    result = _parse_simple_yaml(yaml_file)
    assert result == {"key1": "value1", "key2": "value2"}


def test_personal_paths_set_is_complete() -> None:
    """All personal path names should be documented in _PERSONAL_PATHS."""
    # This test ensures we don't accidentally remove a personal path entry
    assert "desktop_dir" in _PERSONAL_PATHS
    assert "downloads_dir" in _PERSONAL_PATHS
    assert "wechat_file_dir" in _PERSONAL_PATHS
    assert "company_nas_mount" in _PERSONAL_PATHS


def test_get_path_unknown_raises_without_hint() -> None:
    """Unknown path names (not in DEFAULT_PATHS or _PERSONAL_PATHS) raise plain KeyError."""
    with pytest.raises(KeyError, match="未知路径配置"):
        get_path("nonexistent_path_xyz")
