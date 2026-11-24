from utils import config_manager
from utils.config_manager import ConfigManager, DEFAULT_CONFIG


def _patch(monkeypatch, tmp_path):
    cfg = tmp_path / "data" / "config.json"
    monkeypatch.setattr(config_manager, "CONFIG_PATH", str(cfg))
    monkeypatch.setattr(config_manager, "DATA_DIR", str(tmp_path / "data"))
    return cfg


def test_missing_file_returns_default(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    assert ConfigManager.load_config() == DEFAULT_CONFIG


def test_corrupt_json_returns_default(monkeypatch, tmp_path):
    cfg = _patch(monkeypatch, tmp_path)
    cfg.parent.mkdir()
    cfg.write_text("{not json", encoding="utf-8")
    assert ConfigManager.load_config() == DEFAULT_CONFIG


def test_save_then_load_roundtrip(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    assert ConfigManager.save_config({"interval_minutes": 25}) is True
    assert ConfigManager.load_config()["interval_minutes"] == 25
