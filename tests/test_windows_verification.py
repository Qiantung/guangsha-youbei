import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.service import Service


def test_verification_uses_utf8_with_gbk_default(tmp_path, monkeypatch):
    """Emulate Windows' GBK default while reading an actual UTF-8 report."""
    root = tmp_path / "application"
    (root / "verification").mkdir(parents=True)
    report = root / "verification/results.json"
    expected = {"checks": ["完整链路与参考模式", "兑换冲正"]}
    report.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
    service = Service(tmp_path / "demo.sqlite3")
    app = create_app(service)
    original = Path.read_text
    encodings = []

    def windows_read_text(path, encoding=None, errors=None, **kwargs):
        if path == report:
            encodings.append(encoding)
            return path.read_bytes().decode(encoding or "cp936", errors or "strict")
        return original(path, encoding=encoding, errors=errors, **kwargs)

    monkeypatch.setattr(importlib.import_module("backend.app"), "ROOT", root)
    monkeypatch.setattr(Path, "read_text", windows_read_text)
    response = TestClient(app).get("/api/verification")
    assert response.status_code == 200
    assert response.json() == expected
    assert encodings == ["utf-8"]
