import pytest
import requests
import xml.etree.ElementTree as ET
from src.ingestion.relatics_client import RelaticsClient, TokenRequestError

@pytest.fixture
def client():
    return RelaticsClient(client_id="id", client_secret="secret", environment="test")

@pytest.fixture
def relatics_api_response():
    """Return relatics SOAP response"""
    return b"""
    <!--Relatics setting(s): Schema version = 2.0-->
<Report ReportName="DIP-Elements" GeneratedOn="2026-07-31" EnvironmentID="df42d6a9-6ffe-4ddb-bf9a-b3ed6f250ef7"
    EnvironmentName="cwd.relaticsonline.com" EnvironmentURL="https://cwd.relaticsonline.com/"
    WorkspaceID="210b2918-b359-4892-a23b-bf96ad23d82f" WorkspaceName="Zandkreeksluis - Clone CORE" TargetDevice="Pc">
    <Elements>
        <Project_CORE Element="Actie" ElementID="abdc7184-9b2e-e911-a2d5-00155d641103" />
        <Project_CORE Element="Afwijking" ElementID="aa982e98-7b2f-e911-a2d5-00155d641103" />
    </Elements>
</Report>
    """

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

def test_get_token_400(client, mocker):
    """
    Test when you don't supply any credentials.
    """
    mock_res = mocker.Mock()
    mock_res.status_code = 400
    mock_res.text = '{"error": "invalid_client", "error_description": "Client credentials could not be retrieved through the Authorization header."}'
    
    mocker.patch("src.ingestion.relatics_client.requests.post", return_value=mock_res)

    with pytest.raises(TokenRequestError) as exc_info:
        client._get_token()
    print(exc_info.value)
    assert str(exc_info.value) == 'Token request failed with status code 400: {"error": "invalid_client", "error_description": "Client credentials could not be retrieved through the Authorization header."}'

def test_get_token_changed(client, mocker):
    """
    Test when structure of token changes
    """
    mock_res = mocker.Mock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "token": "fake-token", # Different token name
        "token_type": "Bearer"
    }
    
    mocker.patch("src.ingestion.relatics_client.requests.post", return_value=mock_res)

    with pytest.raises(TokenRequestError) as exc_info:
        client._get_token()
    assert str(exc_info.value) == 'Missing access_token or token_type in response'

def test_parse_xml_success(client, relatics_api_response, mocker):
    """
    Test the succesful xml response
    """
    mocker.patch.object(client, "_get_token", return_value=("fake-token", "Bearer")) # Mock the response so you dont actually make the API call
    
    mock_res = mocker.Mock()
    mock_res.status_code = 200
    mock_res.content = relatics_api_response

    mocker.patch("src.ingestion.relatics_client.requests.get", return_value=mock_res)
    xml = client.get_request("workspaceid", "operation")

    assert "Report" in xml.tag
    assert xml.find(".//Project_CORE") is not None
    assert xml.find("Elements") is not None