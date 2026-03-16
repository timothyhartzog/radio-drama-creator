"""Tests for the FastAPI web application."""

import io

import pytest

from fastapi.testclient import TestClient

from radio_drama_creator.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "calibre_installed" in data
        assert "ffmpeg_installed" in data


class TestModelsEndpoint:
    def test_list_models(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "script" in data
        assert "tts" in data


class TestUpload:
    def test_upload_txt_file(self, client):
        content = b"Hello world. This is a test document."
        resp = client.post("/api/upload", files={"file": ("test.txt", io.BytesIO(content), "text/plain")})
        assert resp.status_code == 200
        data = resp.json()
        assert "file_id" in data
        assert data["filename"] == "test.txt"

    def test_upload_unsupported_type(self, client):
        resp = client.post("/api/upload", files={"file": ("test.exe", io.BytesIO(b"data"), "application/octet-stream")})
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_empty_file(self, client):
        resp = client.post("/api/upload", files={"file": ("test.txt", io.BytesIO(b""), "text/plain")})
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


class TestExtractText:
    def test_extract_native(self, client):
        upload = client.post("/api/upload", files={"file": ("test.txt", io.BytesIO(b"Hello world test content here."), "text/plain")})
        file_id = upload.json()["file_id"]
        resp = client.post("/api/extract-text", data={"file_id": file_id, "method": "native"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["char_count"] > 0

    def test_extract_invalid_method(self, client):
        upload = client.post("/api/upload", files={"file": ("test.txt", io.BytesIO(b"Hello"), "text/plain")})
        file_id = upload.json()["file_id"]
        resp = client.post("/api/extract-text", data={"file_id": file_id, "method": "invalid"})
        assert resp.status_code == 400

    def test_extract_invalid_file_id(self, client):
        resp = client.post("/api/extract-text", data={"file_id": "nonexistent123", "method": "native"})
        assert resp.status_code == 404


class TestJobStatus:
    def test_nonexistent_job(self, client):
        resp = client.get("/api/jobs/nonexistent123")
        assert resp.status_code == 404

    def test_invalid_job_id(self, client):
        resp = client.get("/api/jobs/../../etc")
        assert resp.status_code in (400, 404)


class TestConvert:
    def test_invalid_format(self, client):
        resp = client.post("/api/convert", data={
            "job_id": "abc123",
            "filename": "test.wav",
            "output_format": "invalid_format",
        })
        assert resp.status_code in (400, 404)  # 400 for bad format or 404 for missing job


class TestIndexPage:
    def test_index_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Radio Drama Creator" in resp.text


class TestCatalogPage:
    def test_catalog_loads(self, client):
        resp = client.get("/catalog")
        assert resp.status_code == 200
        assert "Function" in resp.text


class TestProducePipeline:
    def test_produce_with_script_renderer(self, client):
        content = (
            b"Inspector Clarke walked through the dark street. "
            b"The rain hammered the cobblestones. Mrs Pemberton watched from her window. "
            b"The danger was growing. He whispered about the secret threat. "
            b"The city held its breath as the night deepened further."
        )
        upload = client.post("/api/upload", files={"file": ("story.txt", io.BytesIO(content), "text/plain")})
        file_id = upload.json()["file_id"]

        resp = client.post("/api/produce", data={
            "file_id": file_id,
            "genre": "mystery",
            "scenes": 2,
            "lines_per_scene": 4,
            "script_backend": "heuristic",
            "renderer": "script",
            "tone": "suspenseful",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "complete"
        job_id = data["job_id"]

        files_resp = client.get(f"/api/jobs/{job_id}/files")
        assert files_resp.status_code == 200
        file_names = [f["name"] for f in files_resp.json()["files"]]
        assert "script.txt" in file_names

    def test_produce_invalid_backend(self, client):
        upload = client.post("/api/upload", files={"file": ("test.txt", io.BytesIO(b"Some text."), "text/plain")})
        file_id = upload.json()["file_id"]
        resp = client.post("/api/produce", data={
            "file_id": file_id,
            "script_backend": "invalid_backend",
        })
        assert resp.status_code == 400
