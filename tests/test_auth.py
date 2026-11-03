import os
import json
import pytest
from unittest.mock import MagicMock
from src.auth import get_credentials, get_sheets_service

def test_get_credentials_missing(monkeypatch):
    monkeypatch.delenv("GCP_SA_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    if os.path.exists("credentials.json"):
        monkeypatch.setattr(os.path, "exists", lambda x: False)
    
    assert get_credentials() is None

def test_get_sheets_service_raises_when_no_credentials(monkeypatch):
    monkeypatch.setattr("src.auth.get_credentials", lambda: None)
    with pytest.raises(RuntimeError) as exc_info:
        get_sheets_service()
    assert "Chưa cấu hình Service Account" in str(exc_info.value)

def test_get_credentials_from_env_json(monkeypatch):
    fake_creds = {
        "type": "service_account",
        "project_id": "test-project",
        "client_email": "test@test-project.iam.gserviceaccount.com"
    }
    mock_creds = MagicMock()
    mock_creds.service_account_email = "test@test-project.iam.gserviceaccount.com"
    monkeypatch.setattr("src.auth.Credentials.from_service_account_info", lambda info, scopes: mock_creds)
    monkeypatch.setenv("GCP_SA_KEY", json.dumps(fake_creds))
    
    creds = get_credentials()
    assert creds is not None
    assert creds.service_account_email == "test@test-project.iam.gserviceaccount.com"
