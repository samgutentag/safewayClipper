from pathlib import Path
import pytest
from clipper.config import load_config, BANNER_BASE_URLS

def test_banner_maps_to_base_url(tmp_path, monkeypatch):
    monkeypatch.delenv("PUSHOVER_TOKEN", raising=False)
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'banner = "vons"\n'
        'session_path = "session.json"\n'
        '[pushover]\ntoken = "t"\nuser = "u"\n'
    )
    cfg = load_config(cfg_file)
    assert cfg.base_url == "https://www.vons.com"
    assert cfg.pushover_token == "t"
    assert cfg.notify_on_success is True

def test_env_overrides_pushover(tmp_path, monkeypatch):
    monkeypatch.setenv("PUSHOVER_TOKEN", "env-token")
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('banner = "vons"\nsession_path = "s.json"\n')
    cfg = load_config(cfg_file)
    assert cfg.pushover_token == "env-token"

def test_unknown_banner_raises(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('banner = "kroger"\nsession_path = "s.json"\n')
    with pytest.raises(ValueError):
        load_config(cfg_file)

def test_missing_banner_raises_valueerror(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('session_path = "s.json"\n')
    with pytest.raises(ValueError, match="banner"):
        load_config(cfg_file)

def test_missing_session_path_raises_valueerror(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('banner = "vons"\n')
    with pytest.raises(ValueError, match="session_path"):
        load_config(cfg_file)
