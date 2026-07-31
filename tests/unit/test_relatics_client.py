import pytest
import requests
import xml.etree.ElementTree as ET
from src.ingestion.relatics_client import RelaticsClient

@pytest.fixture
def client():
    return RelaticsClient(client_id="id", client_secret="secret", environment="test")

def test_get_token_success(client, mocker):
    mock_res = mocker.Mock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "access_token": "fake-token",
        "token_type": "Bearer"
    }

    # Target the full import path where requests is used
    mocker.patch("src.ingestion.relatics_client.requests.post", return_value=mock_res)

    token, token_type = client._get_token()

    assert token == "fake-token"
    assert token_type == "Bearer"

def test_get_token_400(client,mocker):
    pass