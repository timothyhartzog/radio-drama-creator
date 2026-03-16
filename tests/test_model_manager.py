"""Tests for the model manager and related API endpoints."""

from unittest.mock import patch

import pytest

from radio_drama_creator.model_manager import (
    LocalModel,
    check_model_downloaded,
    get_cache_dir,
    get_cache_summary,
    list_local_models,
)


class TestLocalModel:
    def test_size_properties(self):
        m = LocalModel(
            repo_id="test/model",
            size_bytes=1024 * 1024 * 500,  # 500 MB
            nb_files=10,
            last_accessed=0,
            last_modified=0,
            revisions=["abc123"],
            cache_path="/tmp/test",
        )
        assert m.size_mb == 500.0
        assert abs(m.size_gb - 0.488) < 0.01

    def test_to_dict(self):
        m = LocalModel(
            repo_id="org/model",
            size_bytes=1024,
            nb_files=2,
            last_accessed=1000.0,
            last_modified=2000.0,
            revisions=["rev1"],
            cache_path="/cache",
        )
        d = m.to_dict()
        assert d["repo_id"] == "org/model"
        assert "size_mb" in d
        assert "size_gb" in d


class TestGetCacheDir:
    def test_returns_path(self):
        path = get_cache_dir()
        assert "huggingface" in str(path).lower() or "cache" in str(path).lower()


class TestListLocalModels:
    def test_returns_list(self):
        result = list_local_models()
        assert isinstance(result, list)


class TestGetCacheSummary:
    def test_returns_dict(self):
        summary = get_cache_summary()
        assert "total_models" in summary
        assert "total_size_gb" in summary
        assert "cache_dir" in summary
        assert "disk_free_gb" in summary


class TestCheckModelDownloaded:
    def test_nonexistent_model(self):
        assert check_model_downloaded("nonexistent/model-xyz") is False


# --- Web API tests ---

from fastapi.testclient import TestClient
from radio_drama_creator.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestModelsPageEndpoint:
    def test_models_page_loads(self, client):
        resp = client.get("/models")
        assert resp.status_code == 200
        assert "Model Manager" in resp.text

    def test_models_page_has_recommendations(self, client):
        resp = client.get("/models")
        assert "Default" in resp.text
        assert "Drama" in resp.text


class TestLocalModelsAPI:
    def test_list_local(self, client):
        resp = client.get("/api/models/local")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "summary" in data
        assert "total_models" in data["summary"]


class TestRegistryAPI:
    def test_list_registry(self, client):
        resp = client.get("/api/models/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert "script" in data
        assert "tts" in data
        for model in data["script"]:
            assert "key" in model
            assert "repo" in model
            assert "downloaded" in model

    def test_registry_has_all_roles(self, client):
        resp = client.get("/api/models/registry")
        data = resp.json()
        assert len(data["script"]) >= 2
        assert len(data["tts"]) >= 3


class TestDeleteModelAPI:
    def test_delete_nonexistent(self, client):
        resp = client.post("/api/models/delete", data={"repo_id": "nonexistent/model"})
        assert resp.status_code == 422

    def test_delete_empty_id(self, client):
        resp = client.post("/api/models/delete", data={"repo_id": ""})
        assert resp.status_code in (400, 422)
