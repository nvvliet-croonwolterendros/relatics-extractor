import json
import pytest
from relatics_extractor import RelaticsClient

def test_api_call():
    with open("configuration.json") as f:
        secrets = json.load(f)

    client = RelaticsClient(client_id=secrets["client_id"], client_secret=secrets["client_secret"], environment=secrets["environment"])
    xml = client.get_request(workspace_id="210b2918-b359-4892-a23b-bf96ad23d82f", operation="dip_elements")
    assert "Report" in xml.tag
    assert xml.find(".//Project_CORE") is not None
    assert xml.find("Elements") is not None