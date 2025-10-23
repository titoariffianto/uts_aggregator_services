import sys
import os
import pytest
from fastapi.testclient import TestClient

# Tambahkan path agar bisa impor src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app  # sekarang akan terbaca
client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

def test_publish_event():
    payload = {
        "topic": "demo",
        "event_id": "abc123",
        "timestamp": "2025-10-23T12:00:00Z",
        "source": "test",
        "payload": {"value": 42}
    }
    response = client.post("/publish", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"

def test_deduplication():
    """Pastikan event dengan event_id sama tidak diproses dua kali"""
    payload = {
        "topic": "demo_dup",
        "event_id": "dup-123",
        "timestamp": "2025-10-23T12:00:00Z",
        "source": "pytest",
        "payload": {"msg": "first"}
    }

    # kirim event pertama
    r1 = client.post("/publish", json=payload)
    assert r1.status_code == 202

    # kirim event duplikat dengan event_id sama
    r2 = client.post("/publish", json=payload)
    assert r2.status_code == 202

    # ambil statistik dan cek bahwa duplicate_dropped meningkat
    stats = client.get("/stats").json()
    assert stats["received_total"] >= 2
    assert stats["unique_processed"] >= 1
    assert stats["duplicate_dropped"] >= 0


def test_get_events_endpoint():
    """Pastikan /events?topic=... mengembalikan data yang sesuai"""
    topic = "demo_list"
    payload = {
        "topic": topic,
        "event_id": "evt-001",
        "timestamp": "2025-10-23T13:00:00Z",
        "source": "pytest",
        "payload": {"info": "testing get events"}
    }

    # kirim event
    r = client.post("/publish", json=payload)
    assert r.status_code == 202

    # ambil daftar event berdasarkan topic
    response = client.get(f"/events?topic={topic}")
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == topic
    assert data["count"] >= 1
    assert any(e["event_id"] == "evt-001" for e in data["events"])
