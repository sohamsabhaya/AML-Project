"""API tests using a fake model service. Run with ``pytest`` from backend/."""
from __future__ import annotations

import json
import math
import re

from app import config
from app.preprocess import sanitize_filename

from .conftest import make_image_bytes, upload


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False
    assert body["classes"] == ["glioma", "meningioma", "notumor", "pituitary"]
    assert set(body["models"]) == {"resnet50", "custom_cnn"}
    assert set(body["models"]["resnet50"]) == {"available", "loaded"}
    assert isinstance(body["tensorflow_available"], bool)
    assert body["demo"] is False


def test_models_reads_csv(client):
    resp = client.get("/api/models")
    assert resp.status_code in (200, 404)  # 404 only if the csv is missing from the checkout
    if resp.status_code == 200:
        ids = {m["id"] for m in resp.json()["models"]}
        assert ids == {"custom_cnn", "resnet50"}


def test_analyze_png(client, png_bytes):
    resp = upload(client, png_bytes, heatmap="true")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["predicted_class"] == "meningioma"
    assert body["predicted_label"] == "Meningioma"
    assert body["confidence"] == 0.85
    assert body["model_version"] == "resnet50-v1"
    assert body["disclaimer"] == config.DISCLAIMER
    assert body["image_url"] == f"/api/analyses/{body['id']}/image"
    assert body["heatmap_url"] == f"/api/analyses/{body['id']}/heatmap"
    assert client.get(body["image_url"]).headers["content-type"] == "image/png"
    assert client.get(body["heatmap_url"]).headers["content-type"] == "image/png"


def test_preprocess_is_raw_0_255(client, fake_service):
    upload(client, make_image_bytes("PNG", (100, 80), "RGB"))
    assert fake_service.last_array is not None
    assert fake_service.last_array.max() > 1.5  # not rescaled to [0, 1]


def test_analyze_without_heatmap_and_custom_model(client, png_bytes):
    body = upload(client, png_bytes, heatmap="false", model="custom_cnn").json()
    assert body["heatmap_url"] is None
    assert body["model_version"] == "custom_cnn-v1"
    assert client.get(f"/api/analyses/{body['id']}/heatmap").status_code == 404


def test_heatmap_failure_does_not_fail_analysis(client, fake_service, png_bytes):
    fake_service.heatmap_fails = True
    resp = upload(client, png_bytes)
    assert resp.status_code == 200
    assert resp.json()["heatmap_url"] is None


def test_unknown_model_is_400(client, png_bytes):
    assert upload(client, png_bytes, model="nope").status_code == 400


def test_invalid_extension_is_415(client):
    resp = upload(client, b"hello", name="notes.txt", ctype="text/plain")
    assert resp.status_code == 415
    assert "detail" in resp.json()


def test_fake_image_with_png_extension_is_400(client):
    assert upload(client, b"this is not an image").status_code == 400


def test_empty_file_is_400(client):
    assert upload(client, b"").status_code == 400


def test_gif_renamed_to_png_is_415(client):
    assert upload(client, make_image_bytes("GIF")).status_code == 415


def test_oversize_is_413(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    assert upload(client, b"\x89PNG" + b"0" * 2000).status_code == 413


def test_missing_file_field_is_400(client):
    assert client.post("/api/analyze").status_code == 400


def test_model_unavailable_is_503(client, fake_service, png_bytes):
    fake_service.available = False
    resp = upload(client, png_bytes)
    assert resp.status_code == 503
    assert "TensorFlow" in resp.json()["detail"]


def test_list_pagination_search_filter(client, fake_service, png_bytes):
    classes = [[0.9, 0.04, 0.03, 0.03], [0.1, 0.8, 0.05, 0.05], [0.1, 0.1, 0.7, 0.1]]
    for i, probs in enumerate(classes * 2):  # 6 analyses
        fake_service.probs = probs
        assert upload(client, png_bytes, name=f"patient_{i}.png").status_code == 200

    page1 = client.get("/api/analyses", params={"page": 1, "page_size": 4}).json()
    assert page1["total"] == 6 and len(page1["items"]) == 4 and page1["page_size"] == 4
    page2 = client.get("/api/analyses", params={"page": 2, "page_size": 4}).json()
    assert len(page2["items"]) == 2
    assert page1["items"][0]["filename"] == "patient_5.png"  # newest first

    by_label = client.get("/api/analyses", params={"label": "glioma"}).json()
    assert by_label["total"] == 2
    assert {i["predicted_class"] for i in by_label["items"]} == {"glioma"}

    found = client.get("/api/analyses", params={"search": "patient_3"}).json()
    assert found["total"] == 1
    # LIKE wildcards in user input must be treated literally
    assert client.get("/api/analyses", params={"search": "%"}).json()["total"] == 0

    assert client.get("/api/analyses", params={"label": "bogus"}).status_code == 400
    assert client.get("/api/analyses", params={"page": 0}).status_code == 400


def test_get_and_delete(client, png_bytes):
    body = upload(client, png_bytes).json()
    aid = body["id"]
    assert client.get(f"/api/analyses/{aid}").json()["id"] == aid
    assert client.delete(f"/api/analyses/{aid}").status_code == 200
    assert client.get(f"/api/analyses/{aid}").status_code == 404
    assert client.get(f"/api/analyses/{aid}/image").status_code == 404
    assert client.delete(f"/api/analyses/{aid}").status_code == 404


def test_delete_removes_files(client, png_bytes, tmp_path):
    aid = upload(client, png_bytes).json()["id"]
    data = tmp_path / "data"
    assert list((data / "uploads").iterdir()) and list((data / "heatmaps").iterdir())
    client.delete(f"/api/analyses/{aid}")
    assert not list((data / "uploads").iterdir())
    assert not list((data / "heatmaps").iterdir())


def test_bad_ids_are_404(client):
    assert client.get("/api/analyses/not-an-id").status_code == 404
    assert client.get("/api/analyses/..%2F..%2Fetc").status_code == 404


def test_report_is_pdf(client, png_bytes):
    aid = upload(client, png_bytes, name="<b>x</b>&.png").json()["id"]
    resp = client.get(f"/api/analyses/{aid}/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_report_without_heatmap(client, png_bytes):
    aid = upload(client, png_bytes, heatmap="false").json()["id"]
    assert client.get(f"/api/analyses/{aid}/report").content.startswith(b"%PDF")


def test_stats(client, fake_service, png_bytes):
    assert client.get("/api/stats").json() == {
        "total_scans": 0, "last_7_days": 0, "average_confidence": 0.0,
        "by_class": {c: 0 for c in config.CLASSES},
    }
    upload(client, png_bytes)
    stats = client.get("/api/stats").json()
    assert stats["total_scans"] == 1 and stats["last_7_days"] == 1
    assert stats["by_class"]["meningioma"] == 1
    assert stats["average_confidence"] == 0.85


def test_cors_allows_vite_origin(client):
    resp = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\me\\scan 1.png") == "scan 1.png"
    assert sanitize_filename("") == "upload"
    assert len(sanitize_filename("a" * 500 + ".png")) <= 100


# -- contract v1.1 ----------------------------------------------------------
def test_safety_fields_confident(client, png_bytes):
    body = upload(client, png_bytes).json()
    assert body["low_confidence"] is False
    assert body["confidence_threshold"] == config.CONFIDENCE_THRESHOLD
    assert [t["class"] for t in body["top2"]] == ["meningioma", "notumor"]
    assert body["top2"][0]["label"] == "Meningioma"
    expected = -sum(p * math.log(p) for p in [0.05, 0.85, 0.06, 0.04])
    assert abs(body["entropy"] - expected) < 1e-3
    assert body["model_id"] == "resnet50"
    assert body["comparison"] is None


def test_low_confidence_flag(client, fake_service, png_bytes):
    fake_service.probs = [0.3, 0.3, 0.2, 0.2]
    body = upload(client, png_bytes).json()
    assert body["low_confidence"] is True


def test_threshold_from_config(client, fake_service, png_bytes, monkeypatch):
    monkeypatch.setattr(config, "CONFIDENCE_THRESHOLD", 0.9)
    body = upload(client, png_bytes).json()  # top probability 0.85 < 0.9
    assert body["low_confidence"] is True and body["confidence_threshold"] == 0.9


def test_entropy_bounds(client, fake_service, png_bytes):
    fake_service.probs = [0.25, 0.25, 0.25, 0.25]
    assert abs(upload(client, png_bytes).json()["entropy"] - math.log(4)) < 1e-3
    fake_service.probs = [1.0, 0.0, 0.0, 0.0]
    assert upload(client, png_bytes).json()["entropy"] == 0


def test_analyze_both_models(client, fake_service, png_bytes):
    fake_service.probs_by_model = {
        "resnet50": [0.05, 0.85, 0.06, 0.04],
        "custom_cnn": [0.7, 0.1, 0.1, 0.1],
    }
    body = upload(client, png_bytes, model="both").json()
    assert body["model_id"] == "resnet50" and body["predicted_class"] == "meningioma"
    comp = body["comparison"]
    assert comp["resnet50"]["predicted_class"] == "meningioma"
    assert comp["custom_cnn"]["predicted_class"] == "glioma"
    assert comp["agree"] is False
    assert set(comp["custom_cnn"]) == {"predicted_class", "confidence", "probabilities"}
    # comparison survives a round trip through storage
    assert client.get(f"/api/analyses/{body['id']}").json()["comparison"] == comp


def test_analyze_both_agree(client, png_bytes):
    assert upload(client, png_bytes, model="both").json()["comparison"]["agree"] is True


def test_ids_are_unguessable(client, png_bytes):
    ids = {upload(client, png_bytes).json()["id"] for _ in range(3)}
    assert len(ids) == 3
    assert all(re.fullmatch(r"[A-Za-z0-9_-]{22}", i) for i in ids)


def test_list_items_include_safety_fields(client, png_bytes):
    upload(client, png_bytes)
    item = client.get("/api/analyses").json()["items"][0]
    assert {"low_confidence", "top2", "entropy", "model_id"} <= set(item)


def test_purge_requires_confirm(client, png_bytes, tmp_path):
    upload(client, png_bytes)
    upload(client, png_bytes)
    assert client.delete("/api/analyses").status_code == 400
    assert client.delete("/api/analyses", params={"confirm": "false"}).status_code == 400
    assert client.get("/api/stats").json()["total_scans"] == 2
    resp = client.delete("/api/analyses", params={"confirm": "true"})
    assert resp.status_code == 200 and resp.json()["deleted"] == 2
    assert client.get("/api/stats").json()["total_scans"] == 0
    assert not list((tmp_path / "data" / "uploads").iterdir())


def test_insights_unavailable(client, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "INSIGHTS_JSON", tmp_path / "missing.json")
    resp = client.get("/api/models/insights")
    assert resp.status_code == 200
    assert resp.json() == {"status": "unavailable", "models": []}


def test_insights_reads_file(client, monkeypatch, tmp_path):
    path = tmp_path / "insights.json"
    payload = {"status": "verified_from_notebook_outputs", "models": [{"id": "resnet50", "accuracy": 0.9}]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(config, "INSIGHTS_JSON", path)
    assert client.get("/api/models/insights").json() == payload


def test_retention_purge_at_startup(tmp_path, fake_service, png_bytes, monkeypatch):
    import sqlite3

    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.storage import Storage

    storage = Storage(tmp_path / "data")
    first = storage.create(
        filename="old.png", predicted_class="glioma", confidence=0.9,
        probabilities={"glioma": 0.9, "meningioma": 0.05, "notumor": 0.03, "pituitary": 0.02},
        model_version="resnet50-v1", model_id="resnet50", image_bytes=png_bytes,
        image_ext=".png", heatmap_png=None,
    )
    storage.create(
        filename="new.png", predicted_class="glioma", confidence=0.9,
        probabilities={"glioma": 0.9, "meningioma": 0.05, "notumor": 0.03, "pituitary": 0.02},
        model_version="resnet50-v1", model_id="resnet50", image_bytes=png_bytes,
        image_ext=".png", heatmap_png=None,
    )
    with sqlite3.connect(storage.db_path) as conn:
        conn.execute("UPDATE analyses SET created_at = '2000-01-01T00:00:00Z' WHERE id = ?", (first["id"],))
    monkeypatch.setattr(config, "RETENTION_DAYS", 30)
    with TestClient(create_app(storage=storage, model_service=fake_service)) as c:
        body = c.get("/api/analyses").json()
    assert body["total"] == 1 and body["items"][0]["filename"] == "new.png"


def test_legacy_rows_are_upgraded(tmp_path, png_bytes):
    import sqlite3

    from app.storage import Storage

    data = tmp_path / "data"
    (data / "uploads").mkdir(parents=True)
    (data / "heatmaps").mkdir(parents=True)
    (data / "uploads" / "abcd1234.png").write_bytes(png_bytes)
    with sqlite3.connect(data / "analyses.db") as conn:
        conn.execute(
            "CREATE TABLE analyses (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, filename TEXT NOT NULL,"
            " predicted_class TEXT NOT NULL, confidence REAL NOT NULL, probabilities TEXT NOT NULL,"
            " model_version TEXT NOT NULL, image_file TEXT NOT NULL, heatmap_file TEXT)"
        )
        conn.execute(
            "INSERT INTO analyses VALUES ('abcd1234', '2026-01-01T00:00:00Z', 'a.png', 'glioma', 0.5,"
            " ?, 'resnet50-v1', 'abcd1234.png', NULL)",
            (json.dumps({"glioma": 0.5, "meningioma": 0.3, "notumor": 0.1, "pituitary": 0.1}),),
        )
    rec = Storage(data).get("abcd1234")
    assert rec is not None and rec["low_confidence"] is True
    assert rec["model_id"] == "resnet50" and len(rec["top2"]) == 2
