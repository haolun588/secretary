import logging
import re
from logging.handlers import RotatingFileHandler

import pytest

from utils import logger as logger_mod


@pytest.fixture(autouse=True)
def reset_logging():
    logger_mod._reset_for_tests()
    yield
    logger_mod._reset_for_tests()


def _root():
    return logging.getLogger(logger_mod.ROOT_LOGGER_NAME)


def _file_handlers():
    return [h for h in _root().handlers if isinstance(h, logging.FileHandler)]


def test_writes_to_log_file(tmp_path):
    logger_mod.setup_logging(log_dir=str(tmp_path / "logs"))
    logger_mod.get_logger("tests.sample").info("你好 log")
    for h in _file_handlers():
        h.flush()
    text = (tmp_path / "logs" / logger_mod.LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "你好 log" in text
    assert "[INFO]" in text
    assert re.search(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[", text, re.M)
    assert "secretary.tests.sample" in text


def test_setup_is_idempotent(tmp_path):
    logger_mod.setup_logging(log_dir=str(tmp_path))
    count = len(_root().handlers)
    logger_mod.setup_logging(log_dir=str(tmp_path))
    logger_mod.get_logger("a")
    logger_mod.get_logger("b")
    assert len(_root().handlers) == count


def test_get_logger_uses_default_log_dir_lazily(monkeypatch, tmp_path):
    monkeypatch.setattr(logger_mod, "_default_log_dir", lambda: str(tmp_path / "d"))
    logger_mod.get_logger("x").warning("hi")
    assert (tmp_path / "d" / logger_mod.LOG_FILE_NAME).exists()


def test_dir_creation_failure_does_not_crash(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    # log_dir 位於一般檔案之下，makedirs 必定失敗
    logger_mod.setup_logging(log_dir=str(blocker / "logs"))
    logger_mod.get_logger("x").error("不應崩潰")
    assert not _file_handlers()
    assert _root().handlers


def test_no_stdout_uses_null_handler(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(logger_mod.sys, "stdout", None)
    logger_mod.setup_logging(log_dir=str(blocker / "logs"))
    handlers = _root().handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)
    assert not _file_handlers()
    logger_mod.get_logger("x").info("ok")


def test_no_stdout_with_valid_dir_has_file_handler_only(monkeypatch, tmp_path):
    monkeypatch.setattr(logger_mod.sys, "stdout", None)
    logger_mod.setup_logging(log_dir=str(tmp_path / "logs"))
    handlers = _root().handlers
    assert not any(type(h) is logging.StreamHandler for h in handlers)
    assert any(isinstance(h, RotatingFileHandler) for h in handlers)


def test_third_party_loggers_share_file_handler_idempotently(tmp_path):
    logger_mod.setup_logging(log_dir=str(tmp_path))
    logger_mod.setup_logging(log_dir=str(tmp_path))
    for name in logger_mod.THIRD_PARTY_LOGGERS:
        third = logging.getLogger(name)
        assert len([h for h in third.handlers if isinstance(h, RotatingFileHandler)]) == 1
    logger_mod._reset_for_tests()
    for name in logger_mod.THIRD_PARTY_LOGGERS:
        assert not logging.getLogger(name).handlers
