"""Security regression tests."""
from pathlib import Path
from src.tools.dynamic_loader import load_dynamic_tools


def test_dynamic_loader_rejects_python_tools():
    tools = load_dynamic_tools([{"name": "PythonTools"}])
    assert tools == [], "PythonTools must not be instantiated via dynamic loader"


def test_dynamic_loader_rejects_file_tools():
    tools = load_dynamic_tools([{"name": "FileTools"}])
    assert tools == [], "FileTools must not be instantiated via dynamic loader"


def test_dynamic_loader_still_allows_safe_tools():
    tools = load_dynamic_tools([{"name": "DuckDuckGoTools"}])
    assert len(tools) == 1


from unittest.mock import patch
from fastapi.testclient import TestClient


def _make_test_app():
    """Build a minimal FastAPI app with the bearer dependency wired up."""
    from fastapi import FastAPI, Depends
    from src.middleware.api_key import require_bearer_token

    app = FastAPI()

    @app.post("/v1/dynamic-run", dependencies=[Depends(require_bearer_token)])
    def _dummy():
        return {"ok": True}

    return app


def test_dynamic_run_rejects_missing_auth_header():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post("/v1/dynamic-run", json={})
    assert resp.status_code == 403


def test_dynamic_run_rejects_wrong_token():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Bearer wrongtoken"}
        )
    assert resp.status_code == 403


def test_dynamic_run_rejects_non_bearer_scheme():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Basic secret123"}
        )
    assert resp.status_code == 403


def test_dynamic_run_accepts_correct_bearer_token():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Bearer secret123"}
        )
    # 422 = past auth but missing payload fields — acceptable
    assert resp.status_code in (200, 422)


def test_dynamic_run_returns_503_when_key_not_configured():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": ""}, clear=False):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Bearer anything"}
        )
    assert resp.status_code == 503


def test_cors_blocks_unlisted_origin():
    """A request from an unlisted origin must not receive ACAO header."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://allowed.example.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ping", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in resp.headers


def test_cors_allows_listed_origin():
    """A request from a listed origin receives the ACAO header."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://allowed.example.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ping", headers={"Origin": "https://allowed.example.com"})
    assert resp.headers.get("access-control-allow-origin") == "https://allowed.example.com"


def test_upload_filename_strips_path_traversal():
    """Path.name strips directory components from uploaded filenames."""
    malicious = "../../etc/passwd"
    safe_name = Path(malicious).name
    assert safe_name == "passwd"
    assert "/" not in safe_name
    assert "\\" not in safe_name


def test_upload_resolved_path_stays_inside_dept_dir(tmp_path):
    """Resolved destination must be a child of the department directory."""
    dept_dir = tmp_path / "Marketing"
    dept_dir.mkdir()
    safe_filename = Path("../../evil.txt").name  # "evil.txt"
    dest = dept_dir / safe_filename
    assert dest.resolve().is_relative_to(dept_dir.resolve())
