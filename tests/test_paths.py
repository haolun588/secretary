import os

from utils import paths


def _setup(monkeypatch, tmp_path):
    project = tmp_path / "project"
    data = project / "data"
    project.mkdir()
    monkeypatch.setattr(paths, "PROJECT_DIR", str(project))
    monkeypatch.setattr(paths, "DATA_DIR", str(data))
    return project, data


def test_migrate_moves_old_files(monkeypatch, tmp_path):
    project, data = _setup(monkeypatch, tmp_path)
    (project / "config.json").write_text("old", encoding="utf-8")
    result = paths.migrate_legacy_files()
    assert result["moved"] == ["config.json"]
    assert not (project / "config.json").exists()
    assert (data / "config.json").read_text(encoding="utf-8") == "old"


def test_migrate_does_not_overwrite(monkeypatch, tmp_path):
    project, data = _setup(monkeypatch, tmp_path)
    data.mkdir()
    (project / "token.json").write_text("old", encoding="utf-8")
    (data / "token.json").write_text("new", encoding="utf-8")
    result = paths.migrate_legacy_files()
    assert result["skipped_both_exist"] == ["token.json"]
    assert (project / "token.json").read_text(encoding="utf-8") == "old"
    assert (data / "token.json").read_text(encoding="utf-8") == "new"


def test_migrate_single_failure_does_not_affect_others(monkeypatch, tmp_path):
    project, data = _setup(monkeypatch, tmp_path)
    for name in ("config.json", "credentials.json", "token.json"):
        (project / name).write_text(name, encoding="utf-8")

    real_move = paths.shutil.move

    def flaky_move(src, dst, *a, **kw):
        if os.path.basename(src) == "credentials.json":
            raise OSError("boom")
        return real_move(src, dst, *a, **kw)

    monkeypatch.setattr(paths.shutil, "move", flaky_move)
    result = paths.migrate_legacy_files()
    assert sorted(result["moved"]) == ["config.json", "token.json"]
    assert [n for n, _ in result["failed"]] == ["credentials.json"]
    assert (project / "credentials.json").exists()
