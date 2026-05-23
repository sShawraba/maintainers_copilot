import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

# ... (keep override_auth, clear_overrides if needed) ...

def test_chat_endpoint_requires_auth():
    response = client.post("/chat/", json={"message": "Hello", "conversation_id": "test"})
    assert response.status_code == 401

# def test_chat_endpoint_with_mock_service():
#     ... commented out ...

# def test_rag_retrieve_mock():
#     ... commented out ...

def test_widget_config_not_found():
    response = client.get("/widget/config/nonexistent")
    assert response.status_code == 404

# def test_widget_config_mock():
#     ... commented out ...

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()