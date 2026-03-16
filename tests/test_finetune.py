"""Tests for the fine-tuning API endpoints."""

import io
import json

import pytest

from fastapi.testclient import TestClient

from radio_drama_creator.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestFinetunePage:
    def test_page_loads(self, client):
        resp = client.get("/finetune")
        assert resp.status_code == 200
        assert "Fine-Tune Studio" in resp.text

    def test_page_has_nav_links(self, client):
        resp = client.get("/finetune")
        assert 'href="/models"' in resp.text
        assert 'href="/finetune"' in resp.text
        assert 'href="/catalog"' in resp.text

    def test_page_has_step_indicator(self, client):
        resp = client.get("/finetune")
        assert "Upload Data" in resp.text
        assert "Configure" in resp.text
        assert "Train" in resp.text
        assert "Test" in resp.text
        assert "Fuse" in resp.text


class TestFinetuneUploadData:
    def test_upload_valid_jsonl(self, client):
        examples = [
            {"messages": [
                {"role": "system", "content": "You are a writer."},
                {"role": "user", "content": "Write a scene."},
                {"role": "assistant", "content": "NARRATOR: The sun rose."},
            ]},
            {"messages": [
                {"role": "user", "content": "Another scene."},
                {"role": "assistant", "content": "NARRATOR: Rain fell."},
            ]},
        ]
        content = "\n".join(json.dumps(ex) for ex in examples)
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("train.jsonl", io.BytesIO(content.encode()), "application/jsonl")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_examples"] == 2
        assert data["train_examples"] >= 1
        assert "data_id" in data

    def test_upload_text_format(self, client):
        examples = [{"text": "Some training text."}, {"text": "More text."}]
        content = "\n".join(json.dumps(ex) for ex in examples)
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("data.jsonl", io.BytesIO(content.encode()), "application/jsonl")},
        )
        assert resp.status_code == 200

    def test_upload_completions_format(self, client):
        examples = [{"prompt": "Write:", "completion": "Done."}]
        content = json.dumps(examples[0])
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("data.jsonl", io.BytesIO(content.encode()), "application/jsonl")},
        )
        assert resp.status_code == 200

    def test_upload_wrong_extension(self, client):
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400
        assert "jsonl" in resp.json()["detail"].lower()

    def test_upload_empty_file(self, client):
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("train.jsonl", io.BytesIO(b""), "application/jsonl")},
        )
        assert resp.status_code == 400

    def test_upload_invalid_json(self, client):
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("train.jsonl", io.BytesIO(b"not json at all"), "application/jsonl")},
        )
        assert resp.status_code == 422

    def test_upload_missing_keys(self, client):
        content = json.dumps({"foo": "bar"})
        resp = client.post(
            "/api/finetune/upload-data",
            files={"file": ("train.jsonl", io.BytesIO(content.encode()), "application/jsonl")},
        )
        assert resp.status_code == 422


class TestFinetuneStart:
    def test_start_missing_data(self, client):
        resp = client.post(
            "/api/finetune/start",
            data={"data_id": "nonexistent123", "base_model": "test/model"},
        )
        assert resp.status_code == 404

    def test_start_invalid_data_id(self, client):
        resp = client.post(
            "/api/finetune/start",
            data={"data_id": "../../../etc", "base_model": "test/model"},
        )
        assert resp.status_code == 400


class TestFinetuneStatus:
    def test_status_not_found(self, client):
        resp = client.get("/api/finetune/status/nonexistent12")
        assert resp.status_code == 404

    def test_status_invalid_id(self, client):
        resp = client.get("/api/finetune/status/bad-id!")
        assert resp.status_code == 400


class TestFinetuneAdapters:
    def test_list_adapters_empty(self, client):
        resp = client.get("/api/finetune/adapters")
        assert resp.status_code == 200
        data = resp.json()
        assert "adapters" in data
        assert isinstance(data["adapters"], list)


class TestFinetuneTest:
    def test_test_no_adapter(self, client):
        resp = client.post(
            "/api/finetune/test",
            data={
                "base_model": "test/model",
                "adapter_path": "/nonexistent/path",
                "prompt": "Hello",
            },
        )
        # Should reject because path is outside FINETUNE_DIR
        assert resp.status_code == 400

    def test_test_empty_prompt(self, client):
        resp = client.post(
            "/api/finetune/test",
            data={
                "base_model": "test/model",
                "adapter_path": "/tmp/radio_drama_finetune/adapters/test",
                "prompt": "",
            },
        )
        assert resp.status_code in (400, 422)


class TestFinetuneFuse:
    def test_fuse_invalid_adapter(self, client):
        resp = client.post(
            "/api/finetune/fuse",
            data={
                "base_model": "test/model",
                "adapter_path": "/nonexistent/path",
                "output_name": "test_fused",
            },
        )
        assert resp.status_code == 400


class TestNavLinks:
    def test_index_has_finetune_link(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'href="/finetune"' in resp.text

    def test_models_has_finetune_link(self, client):
        resp = client.get("/models")
        assert resp.status_code == 200
        assert 'href="/finetune"' in resp.text

    def test_catalog_has_finetune_link(self, client):
        resp = client.get("/catalog")
        assert resp.status_code == 200
        assert 'href="/finetune"' in resp.text
