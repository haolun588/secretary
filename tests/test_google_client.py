import errno
import importlib.util
import os
import socket
import sys

import pytest
from google_auth_oauthlib.flow import WSGITimeoutError

from services import google_client


class _Req:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeEvents:
    def __init__(self, pages):
        self._pages = pages
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return _Req(self._pages[len(self.calls) - 1])


class _FakeService:
    def __init__(self, pages):
        self.ev = _FakeEvents(pages)

    def events(self):
        return self.ev


def test_list_events_merges_pages():
    service = _FakeService([
        {"items": [{"id": "1"}, {"id": "2"}], "nextPageToken": "tok"},
        {"items": [{"id": "3"}]},
    ])
    items = google_client.list_events(
        service, "2026-03-01T00:00:00+08:00", "2026-04-01T00:00:00+08:00"
    )
    assert [i["id"] for i in items] == ["1", "2", "3"]
    first, second = service.ev.calls
    assert "pageToken" not in first
    assert second["pageToken"] == "tok"
    for call in (first, second):
        assert call["timeMin"] == "2026-03-01T00:00:00+08:00"
        assert call["timeMax"] == "2026-04-01T00:00:00+08:00"
        assert call["singleEvents"] is True
        assert call["calendarId"] == "primary"


def test_list_events_empty():
    service = _FakeService([{}])
    assert google_client.list_events(service, "a", "b") == []


def test_import_has_no_socket_side_effects():
    """以獨立名稱載入一份 google_client 副本（不進 sys.modules），socket 全域狀態不得被改"""
    getaddrinfo = socket.getaddrinfo
    timeout = socket.getdefaulttimeout()
    spec = importlib.util.spec_from_file_location("_gc_copy", google_client.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "_gc_copy" not in sys.modules
    assert socket.getaddrinfo is getaddrinfo
    assert socket.getaddrinfo.__module__ == "socket"
    assert socket.getdefaulttimeout() == timeout


# ---- run_oauth_flow ----

class _FakeCreds:
    valid = True

    def to_json(self):
        return "{}"


class _FakeFlow:
    def __init__(self, behaviors):
        self.behaviors = list(behaviors)
        self.ports = []

    def run_local_server(self, **kwargs):
        self.ports.append(kwargs["port"])
        assert "timeout_seconds" in kwargs
        behavior = self.behaviors.pop(0)
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior


@pytest.fixture
def oauth_env(tmp_path, monkeypatch):
    cred_file = tmp_path / "credentials.json"
    cred_file.write_text("{}", encoding="utf-8")
    holder = {}

    class FakeInstalledAppFlow:
        @staticmethod
        def from_client_secrets_file(path, scopes):
            return holder["flow"]

    monkeypatch.setattr(google_client, "InstalledAppFlow", FakeInstalledAppFlow)
    return holder, str(cred_file), str(tmp_path / "token.json")


def test_oauth_port_in_use_retries_with_random_port_once(oauth_env):
    holder, cred, token = oauth_env
    for err_no in (errno.EADDRINUSE, 10048):
        holder["flow"] = _FakeFlow([OSError(err_no, "in use"), _FakeCreds()])
        creds = google_client.run_oauth_flow(cred, token, timeout=5)
        assert isinstance(creds, _FakeCreds)
        assert holder["flow"].ports == [8080, 0]
    assert os.path.exists(token)


def test_oauth_bind_failure_twice_raises_auth_error(oauth_env):
    holder, cred, token = oauth_env
    holder["flow"] = _FakeFlow([OSError(errno.EADDRINUSE, "x"), OSError(errno.EADDRINUSE, "x")])
    with pytest.raises(google_client.AuthError):
        google_client.run_oauth_flow(cred, token, timeout=5)
    assert holder["flow"].ports == [8080, 0]


def test_oauth_timeout_raises_auth_error_without_retry(oauth_env):
    holder, cred, token = oauth_env
    holder["flow"] = _FakeFlow([WSGITimeoutError("timeout")])
    with pytest.raises(google_client.AuthError) as info:
        google_client.run_oauth_flow(cred, token, timeout=5)
    assert "逾時" in str(info.value)
    assert holder["flow"].ports == [8080]


def test_oauth_non_bind_oserror_does_not_retry(oauth_env):
    holder, cred, token = oauth_env
    holder["flow"] = _FakeFlow([OSError(errno.ECONNRESET, "fetch_token failed")])
    with pytest.raises(google_client.AuthError):
        google_client.run_oauth_flow(cred, token, timeout=5)
    assert holder["flow"].ports == [8080]


def test_oauth_none_or_invalid_creds_raises(oauth_env):
    holder, cred, token = oauth_env
    holder["flow"] = _FakeFlow([None])
    with pytest.raises(google_client.AuthError):
        google_client.run_oauth_flow(cred, token, timeout=5)
    invalid = _FakeCreds()
    invalid.valid = False
    holder["flow"] = _FakeFlow([invalid])
    with pytest.raises(google_client.AuthError):
        google_client.run_oauth_flow(cred, token, timeout=5)
    assert holder["flow"].ports == [8080]


def test_oauth_missing_credentials_file(tmp_path):
    with pytest.raises(google_client.AuthError):
        google_client.run_oauth_flow(str(tmp_path / "nope.json"), str(tmp_path / "t.json"))


# ---- save_token ----

def test_save_token_writes_content_atomically(tmp_path):
    class Creds:
        def to_json(self):
            return '{"token": "abc"}'

    path = tmp_path / "sub" / "token.json"
    google_client.save_token(Creds(), str(path))
    assert path.read_text(encoding="utf-8") == '{"token": "abc"}'
    assert [p.name for p in path.parent.iterdir()] == ["token.json"]  # 無殘留暫存檔
    # 覆寫既有檔
    class Creds2(Creds):
        def to_json(self):
            return '{"token": "def"}'
    google_client.save_token(Creds2(), str(path))
    assert path.read_text(encoding="utf-8") == '{"token": "def"}'
    assert [p.name for p in path.parent.iterdir()] == ["token.json"]


def test_save_token_failure_keeps_old_file_and_cleans_tmp(tmp_path):
    class Bad:
        def to_json(self):
            raise ValueError("boom")

    path = tmp_path / "token.json"
    path.write_text("old", encoding="utf-8")
    with pytest.raises(ValueError):
        google_client.save_token(Bad(), str(path))
    assert path.read_text(encoding="utf-8") == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["token.json"]
