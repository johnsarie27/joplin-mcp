import json

import pytest

from joplin_mcp.config import ConfigError, load_config


def write_config(path, data):
    path.write_text(json.dumps(data))


def test_load_config_valid(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, {"token": "abc", "notebooks": [{"id": "Notebook A", "access": "write"}]})
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    assert load_config() == {"token": "abc", "notebooks": [{"id": "Notebook A", "access": "write"}]}


def test_load_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("JOPLIN_CONFIG", str(tmp_path / "does-not-exist.json"))
    with pytest.raises(ConfigError, match="not found"):
        load_config()


def test_load_config_invalid_json(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text("{not valid json")
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config()


def test_load_config_not_an_object(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, [1, 2, 3])
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    with pytest.raises(ConfigError, match="must contain a JSON object"):
        load_config()


def test_load_config_notebooks_not_a_list(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, {"notebooks": "Notebook A"})
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    with pytest.raises(ConfigError, match="must be a list"):
        load_config()


def test_load_config_notebook_entry_not_an_object(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, {"notebooks": ["Notebook A"]})
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    with pytest.raises(ConfigError, match="must be a JSON object"):
        load_config()


def test_load_config_invalid_access_level(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, {"notebooks": [{"id": "Notebook A", "access": "delete"}]})
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    with pytest.raises(ConfigError, match="Invalid access level"):
        load_config()


def test_load_config_missing_access_defaults_to_read(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, {"notebooks": [{"id": "Notebook A"}]})
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    load_config()  # does not raise


def test_load_config_empty_notebooks_list(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    write_config(config_file, {})
    monkeypatch.setenv("JOPLIN_CONFIG", str(config_file))
    load_config()  # does not raise; `notebooks` defaults to []
